import re
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import glob
import os
import argparse

def parse_changes_md(file_path):
    """
    Parses a changes.md file and returns a list of dictionaries.
    Updated for unified format: version, change_summary, timestamp, code_files, 
    compile_status, job_status, performance_metric, compute_cost, 
    sota_level, technical_comment, next_steps
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Use regex to find all records - updated for new format
    records = []
    # Pattern for unified format
    pattern = re.compile(r"##\s+version:\s*(?P<version>.*?)\n"
                         r"\s*change_summary:\s*\"(?P<summary>.*?)\"\n"
                         r"\s*timestamp:\s*\"(?P<timestamp>.*?)\"\n"
                         r"\s*code_files:\s*\"(?P<code_files>.*?)\"\n"
                         r"(?:.|\n)*?"  # Skip Build & Execution section
                         r"\s*compile_status:\s*(?P<compile_status>.*?)\n"
                         r"\s*job_status:\s*(?P<job_status>.*?)\n"
                         r"\s*performance_metric:\s*\"(?P<performance>.*?)\"\n"
                         r"\s*compute_cost:\s*\"(?P<compute_cost>.*?)\"\n"
                         r"(?:.|\n)*?"  # Skip to Analysis section
                         r"\s*sota_level:\s*(?P<sota_level>.*?)\n"
                         r"\s*technical_comment:\s*\"(?P<technical_comment>.*?)\"\n"
                         r"\s*next_steps:\s*\"(?P<next_steps>.*?)\"", re.DOTALL)

    for match in pattern.finditer(content):
        record = match.groupdict()
        # Extract GFLOPS value from performance_metric
        perf_match = re.search(r'(\d+\.?\d*)', record['performance'])
        if perf_match:
            record['gflops'] = float(perf_match.group(1))
        else:
            record['gflops'] = 0.0
        
        # Extract compute cost as float
        cost_match = re.search(r'(\d+\.?\d*)', record['compute_cost'])
        if cost_match:
            record['node_hours'] = float(cost_match.group(1))
        else:
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
    """Main function to find, parse, and plot all changes.md files."""
    # This script should be run from the project root (e.g., /OpenCodeAT)
    search_path = './**/changes.md'
    all_records = []
    for md_file in glob.glob(search_path, recursive=True):
        print(f"Parsing {md_file}...")
        all_records.extend(parse_changes_md(md_file))

    if not all_records:
        print("No changes.md files found or no records parsed.")
        return

    df = pd.DataFrame(all_records)
    
    # Create output directory if it doesn't exist
    output_dir = './Agent-shared/log_analyzer'
    os.makedirs(output_dir, exist_ok=True)
    
    plot_sota_history(df, os.path.join(output_dir, 'sota_summary.png'))

def main_searcher():
    """Main function for the search tool."""
    parser = argparse.ArgumentParser(description="Search through changes.md files.")
    parser.add_argument('keyword', type=str, help="Keyword to search for in version, summary, or comment.")
    parser.add_argument('--sota_only', action='store_true', help="Only show SOTA records.")
    parser.add_argument('--limit', type=int, default=5, help="Limit the number of results.")
    
    args = parser.parse_args()

    search_path = './**/changes.md'
    all_records = []
    for md_file in glob.glob(search_path, recursive=True):
        all_records.extend(parse_changes_md(md_file))

    if not all_records:
        print("No records found.")
        return

    df = pd.DataFrame(all_records)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values(by='timestamp', ascending=False)

    if args.sota_only:
        # Filter for SOTA records using new format
        df = df[df['sota_level'].str.contains('global|local|project', case=False, na=False)]

    # Search keyword in relevant fields
    df_filtered = df[df.apply(
        lambda row: args.keyword.lower() in str(row['version']).lower() or \
                    args.keyword.lower() in str(row['summary']).lower() or \
                    args.keyword.lower() in str(row['technical_comment']).lower() or \
                    args.keyword.lower() in str(row['next_steps']).lower(),
        axis=1
    )]

    # Print results with updated format
    print(f"--- Found {len(df_filtered)} records for '{args.keyword}' ---")
    for _, row in df_filtered.head(args.limit).iterrows():
        print(f"Version: {row['version']} ({row['timestamp']})")
        print(f"  Summary: {row['summary']}")
        print(f"  Code Files: {row['code_files']}")
        print(f"  Performance: {row['performance']} ({row['compute_cost']})")
        print(f"  SOTA Level: {row['sota_level']}")
        print(f"  Technical Comment: {row['technical_comment']}")
        print(f"  Next Steps: {row['next_steps']}")
        print("-" * 20)


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

