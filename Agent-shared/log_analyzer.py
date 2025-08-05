import re
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import glob
import os
import argparse

def parse_changelog_md(file_path):
    """
    Parses a ChangeLog.md file and returns a list of dictionaries.
    Supports the new ChangeLog format with version entries and details sections.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Use regex to find all records - new ChangeLog format
    records = []
    # Pattern for new ChangeLog format with ### v1.2.3 entries
    version_pattern = r'###\s+v([\d.]+)'
    matches = list(re.finditer(version_pattern, content))
    
    for i, match in enumerate(matches):
        version = f"v{match.group(1)}"
        start = match.start()
        end = matches[i+1].start() if i+1 < len(matches) else len(content)
        entry_content = content[start:end]
        
        record = {"version": version}
        
        # Extract fields from new format
        change_match = re.search(r'\*\*変更点\*\*:\s*"([^"]+)"', entry_content)
        if change_match:
            record["summary"] = change_match.group(1)
        
        result_match = re.search(r'\*\*結果\*\*:\s*([^`]+)\s*`([^`]+)`', entry_content)
        if result_match:
            record["result_type"] = result_match.group(1).strip()
            result_value = result_match.group(2).strip()
            # Extract numeric performance value
            perf_match = re.search(r'(\d+\.?\d*)\s*(MFLOPS|GFLOPS)', result_value)
            if perf_match:
                value = float(perf_match.group(1))
                unit = perf_match.group(2)
                # Convert MFLOPS to GFLOPS for consistency
                record['gflops'] = value / 1000 if unit == 'MFLOPS' else value
            else:
                record['gflops'] = 0.0
        
        # Extract technical comment
        comment_match = re.search(r'\*\*コメント\*\*:\s*"([^"]+)"', entry_content)
        if comment_match:
            record['technical_comment'] = comment_match.group(1)
        
        # Extract compile status from details section
        compile_match = re.search(r'compile\*\*[\s\S]*?status:\s*`([^`]+)`', entry_content)
        if compile_match:
            record['compile_status'] = compile_match.group(1)
        
        # Extract job status
        job_match = re.search(r'job\*\*[\s\S]*?status:\s*`([^`]+)`', entry_content)
        if job_match:
            record['job_status'] = job_match.group(1)
        
        # Extract SOTA scope if present
        sota_match = re.search(r'\*\*sota\*\*[\s\S]*?scope:\s*`([^`]+)`', entry_content)
        if sota_match:
            record['sota_level'] = sota_match.group(1)
        
        # Set default node_hours for now
        record['node_hours'] = 0.0
            
        records.append(record)
    return records

def plot_sota_history(df, output_path):
    """
    Plots the SOTA performance history.
    """
    if df.empty:
        print("No data to plot.")
        return

    # Filter for successful runs with performance data
    df_perf = df[df['gflops'] > 0].copy()
    if df_perf.empty:
        print("No performance data to plot.")
        return
        
    df_perf['timestamp'] = pd.to_datetime(df_perf['timestamp'])
    df_perf = df_perf.sort_values(by='timestamp')

    # Calculate SOTA at each point in time
    df_perf['sota_perf'] = df_perf['gflops'].cummax()

    plt.style.use('seaborn-v0_8-whitegrid')
    fig, ax = plt.subplots(figsize=(12, 7))

    # Plot all attempts
    ax.plot(df_perf['timestamp'], df_perf['gflops'], 'o--', color='lightblue', label='All Attempts', alpha=0.7)

    # Plot SOTA history as a step plot
    ax.step(df_perf['timestamp'], df_perf['sota_perf'], where='post', color='crimson', linewidth=2, label='SOTA Performance')

    # Annotate SOTA points
    sota_points = df_perf[df_perf['gflops'] >= df_perf['sota_perf']]
    for i, row in sota_points.iterrows():
        ax.text(row['timestamp'], row['gflops'], f" {row['gflops']:.1f}\n v{row['version']}", verticalalignment='bottom', fontsize=9)

    ax.set_title('SOTA Performance Over Time', fontsize=16, fontweight='bold')
    ax.set_xlabel('Timestamp', fontsize=12)
    ax.set_ylabel('Performance (GFLOPS)', fontsize=12)
    ax.legend()
    ax.grid(True, which='both', linestyle='--', linewidth=0.5)
    
    # Format y-axis to avoid scientific notation
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.1f'))
    plt.xticks(rotation=45)
    plt.tight_layout()

    print(f"Saving plot to {output_path}")
    plt.savefig(output_path, dpi=150)
    plt.close()

def main_visualizer():
    """Main function to find, parse, and plot all ChangeLog.md files."""
    # This script should be run from the project root (e.g., /VibeCodeHPC)
    search_path = './**/ChangeLog.md'
    all_records = []
    for md_file in glob.glob(search_path, recursive=True):
        print(f"Parsing {md_file}...")
        all_records.extend(parse_changelog_md(md_file))

    if not all_records:
        print("No ChangeLog.md files found or no records parsed.")
        return

    df = pd.DataFrame(all_records)
    
    # Create output directory if it doesn't exist
    output_dir = './Agent-shared/log_analyzer'
    os.makedirs(output_dir, exist_ok=True)
    
    plot_sota_history(df, os.path.join(output_dir, 'sota_summary.png'))

def main_searcher():
    """Main function for the search tool."""
    parser = argparse.ArgumentParser(description="Search through ChangeLog.md files.")
    parser.add_argument('keyword', type=str, help="Keyword to search for in version, summary, or comment.")
    parser.add_argument('--sota_only', action='store_true', help="Only show SOTA records.")
    parser.add_argument('--limit', type=int, default=5, help="Limit the number of results.")
    
    args = parser.parse_args()

    search_path = './**/ChangeLog.md'
    all_records = []
    for md_file in glob.glob(search_path, recursive=True):
        all_records.extend(parse_changelog_md(md_file))

    if not all_records:
        print("No records found.")
        return

    df = pd.DataFrame(all_records)
    # Sort by version (newest first)
    df = df.sort_values(by='version', ascending=False)

    if args.sota_only:
        # Filter for SOTA records using new format
        df = df[df['sota_level'].str.contains('global|local|project', case=False, na=False)]

    # Search keyword in relevant fields
    df_filtered = df[df.apply(
        lambda row: args.keyword.lower() in str(row.get('version', '')).lower() or \
                    args.keyword.lower() in str(row.get('summary', '')).lower() or \
                    args.keyword.lower() in str(row.get('technical_comment', '')).lower(),
        axis=1
    )]

    # Print results with updated format
    print(f"--- Found {len(df_filtered)} records for '{args.keyword}' ---")
    for _, row in df_filtered.head(args.limit).iterrows():
        print(f"Version: {row['version']}")
        print(f"  変更点: {row.get('summary', 'N/A')}")
        print(f"  コメント: {row.get('technical_comment', 'N/A')}")
        print(f"  性能: {row.get('gflops', 0):.1f} GFLOPS")
        print(f"  コンパイル: {row.get('compile_status', 'N/A')}")
        print(f"  ジョブ: {row.get('job_status', 'N/A')}")
        if 'sota_level' in row and row['sota_level']:
            print(f"  SOTA: {row['sota_level']}")
        print("-" * 40)


if __name__ == '__main__':
    # This script can function as both a visualizer and a searcher.
    # To use as a visualizer: python this_script.py visualize
    # To use as a searcher:   python this_script.py search "keyword"
    
    # Simple command-line routing for demonstration
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'visualize':
        main_visualizer()
    elif len(sys.argv) > 1 and sys.argv[1] == 'search':
        # Remove the 'search' command for argparse
        sys.argv = [sys.argv[0]] + sys.argv[2:]
        main_searcher()
    else:
        print("Usage:")
        print("  python this_script.py visualize   # To generate the SOTA plot")
        print("  python this_script.py search <keyword> [--sota_only] [--limit N] # To search logs")
        # As a default action, run the visualizer
        main_visualizer()

