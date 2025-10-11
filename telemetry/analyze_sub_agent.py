
#Bu, alt ajan için analiz betiğidir.
#Amaç: Alt ajanların performansını analiz etmek.

def analyze_performance(data):
    """
    Alt ajanın performans verilerini analiz edeceğim.
    Verilerin bir sözlük listesi olduğu varsayılmaktadır.
    """
    if not data:
        # データがありません。
        print(Hata: Analiz edilecek veri yok.)
        return {}

    total_tasks = len(data)
    successful_tasks = sum(1 for item in data if item.get('status') == 'success')
    failed_tasks = total_tasks - successful_tasks

    print(fToplam görev sayısı: {total_tasks})
    print(fBaşarılı görev sayısı: {successful_tasks})
    print(fBaşarısız olan görev sayısı: {failed_tasks})

    # 結果を返します。
    return {
        'total': total_tasks,
        'success': successful_tasks,
        'failed': failed_tasks
    }

#Kullanım örneği
if __name__ == "__main__":
    sample_data = [
        {'id': 1, 'status': 'success', 'time': 10},
        {'id': 2, 'status': 'failed', 'time': 15},
        {'id': 3, 'status': 'success', 'time': 12},
        {'id': 4, 'status': 'success', 'time': 8},
    ]
    # パフォーマンス分析を実行します。
    results = analyze_performance(sample_data)
    print(Analiz Sonuçları:, results)

    empty_data = []
    # 空のデータで分析を実行します。
    analyze_performance(empty_data)

