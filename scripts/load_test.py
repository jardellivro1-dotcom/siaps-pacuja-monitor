"""
Script de Teste de Carga e Benchmark de Concorrência
Monitor APS Pacujá (IBGE 230990)

Simula acessos concorrentes em múltiplos endpoints do sistema e mensura
latências (p50, p95, p99), throughput (req/s) e taxa de erro,
validando a estabilidade do SQLite em modo WAL e do servidor local.
"""

from __future__ import annotations

import argparse
import statistics
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any


def fetch_url(url: str, timeout: float = 10.0) -> dict[str, Any]:
    start = time.perf_counter()
    status_code = 0
    error_msg = None
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "SiapsBenchmark/1.0 (+http://127.0.0.1:5000)"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status_code = resp.status
            _ = resp.read()
    except urllib.error.HTTPError as exc:
        status_code = exc.code
        error_msg = f"HTTP {exc.code}"
    except Exception as exc:
        error_msg = str(exc)
    elapsed_ms = (time.perf_counter() - start) * 1000.0

    return {
        "url": url,
        "status_code": status_code,
        "elapsed_ms": elapsed_ms,
        "success": 200 <= status_code < 400,
        "error": error_msg,
    }


def run_benchmark(
    base_url: str = "http://127.0.0.1:5000",
    concurrency: int = 25,
    total_requests: int = 250,
) -> dict[str, Any]:
    endpoints = [
        "/healthz",
        "/api/dashboard",
        "/api/status",
        "/api/teams",
        "/api/monthly-tracking",
        "/relatorio",
    ]

    urls_to_test = [f"{base_url}{endpoints[i % len(endpoints)]}" for i in range(total_requests)]

    print(f"\n=======================================================")
    print(f" Iniciando Teste de Carga - Monitor APS Pacujá")
    print(f" Alvo: {base_url}")
    print(f" Concorrência: {concurrency} threads paralelas")
    print(f" Requisições Totais: {total_requests}")
    print(f"=======================================================")

    start_wall = time.perf_counter()
    results = []

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        future_map = {executor.submit(fetch_url, url): url for url in urls_to_test}
        for future in as_completed(future_map):
            results.append(future.result())

    total_time = time.perf_counter() - start_wall

    successes = [r for r in results if r["success"]]
    failures = [r for r in results if not r["success"]]
    latencies = sorted([r["elapsed_ms"] for r in results])

    def calc_percentile(data: list[float], p: float) -> float:
        if not data:
            return 0.0
        k = (len(data) - 1) * (p / 100.0)
        f = int(k)
        c = min(f + 1, len(data) - 1)
        d = k - f
        return data[f] + (data[c] - data[f]) * d

    p50 = calc_percentile(latencies, 50)
    p95 = calc_percentile(latencies, 95)
    p99 = calc_percentile(latencies, 99)
    avg_latency = statistics.mean(latencies) if latencies else 0.0
    throughput = len(results) / total_time if total_time > 0 else 0.0
    error_rate = (len(failures) / len(results) * 100.0) if results else 0.0

    report = {
        "concurrency": concurrency,
        "total_requests": len(results),
        "success_count": len(successes),
        "error_count": len(failures),
        "error_rate_pct": round(error_rate, 2),
        "total_time_seconds": round(total_time, 3),
        "throughput_req_per_sec": round(throughput, 2),
        "latency_min_ms": round(latencies[0], 2) if latencies else 0,
        "latency_avg_ms": round(avg_latency, 2),
        "latency_p50_ms": round(p50, 2),
        "latency_p95_ms": round(p95, 2),
        "latency_p99_ms": round(p99, 2),
        "latency_max_ms": round(latencies[-1], 2) if latencies else 0,
    }

    print(f"\n--- Resultados da Bateria (Concorrência {concurrency}) ---")
    print(f" Tempo Total: {report['total_time_seconds']} s")
    print(f" Throughput: {report['throughput_req_per_sec']} req/s")
    print(f" Sucessos: {report['success_count']} / {report['total_requests']}")
    print(f" Taxa de Erro: {report['error_rate_pct']}%")
    print(f" Latência Média: {report['latency_avg_ms']} ms")
    print(f" Latência p50:   {report['latency_p50_ms']} ms")
    print(f" Latência p95:   {report['latency_p95_ms']} ms")
    print(f" Latência p99:   {report['latency_p99_ms']} ms")
    print(f" Latência Máx:   {report['latency_max_ms']} ms")
    print("-------------------------------------------------------")

    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Teste de Carga do Monitor APS Pacujá")
    parser.add_argument("--url", default="http://127.0.0.1:5000", help="URL base da aplicação")
    parser.add_argument("--concurrency", type=int, default=25, help="Nível de concorrência")
    parser.add_argument("--requests", type=int, default=250, help="Total de requisições")
    args = parser.parse_args()

    run_benchmark(base_url=args.url, concurrency=args.concurrency, total_requests=args.requests)
