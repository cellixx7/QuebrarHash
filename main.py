import time
import hashlib
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Optional, Tuple, List
import multiprocessing
import pandas as pd
import matplotlib.pyplot as plt
import os

# -----------------------------
# ATIVIDADE: Quebrar a hash MD5 do PIN de 9 dígitos
# -----------------------------

TARGET_HASH = "ca6ae33116b93e57b87810a27296fc36"
MAX_N = 1_000_000_000  # 1 bilhão de possibilidades
CHUNK_SIZE = 2_000_000  # 2 milhões por chunk
PROCESS_CONFIGS = [
    (1, 30),   # 1 processo - 30 segundos
    (2, 15),   # 2 processos - 15 segundos
    (4, 7.5),  # 4 processos - 7.5 segundos
    (8, 3.75), # 8 processos - 3.75 segundos
    (12, 2.5)  # 12 processos - 2.5 segundos
]

def clear_screen():
    """Limpa a tela do terminal"""
    os.system('clear' if os.name == 'posix' else 'cls')

def format_pin(n: int) -> str:
    return f"{n:09d}"

def search_range(start: int, end: int, target_hash: str) -> Optional[str]:
    """Busca PIN em um intervalo específico"""
    target_hash = target_hash.lower()
    
    for n in range(start, end):
        pin = format_pin(n)
        if hashlib.md5(pin.encode("utf-8")).hexdigest().lower() == target_hash:
            return pin
    return None

@dataclass
class AttackResult:
    processes: int
    found: Optional[str]
    time: float
    pins_tested: int
    time_limit: float
    pins_per_second: float = 0
    
    def __post_init__(self):
        if self.time > 0:
            self.pins_per_second = self.pins_tested / self.time

def run_attack(target_hash: str, max_n: int, num_processes: int, time_limit: float) -> AttackResult:
    """Executa ataque com limite de tempo"""
    
    # Calcula quantos chunks podemos processar no tempo limite
    est_pins_per_sec = 2_000_000 * num_processes
    max_chunks = int((time_limit * est_pins_per_sec) / CHUNK_SIZE)
    max_chunks = max(1, min(max_chunks, 500))
    
    print(f"   ⏱️  Limite: {time_limit}s | Estimativa: ~{max_chunks} chunks")
    
    # Cria chunks
    ranges = []
    chunks_created = 0
    for start in range(0, max_n, CHUNK_SIZE):
        if chunks_created >= max_chunks:
            break
        end = min(start + CHUNK_SIZE, max_n)
        ranges.append((start, end, target_hash))
        chunks_created += 1
    
    start_time = time.perf_counter()
    found_pin = None
    pins_tested = 0
    
    with ProcessPoolExecutor(max_workers=num_processes) as executor:
        futures = [executor.submit(search_range, *r) for r in ranges]
        
        for future in as_completed(futures):
            if time.perf_counter() - start_time > time_limit:
                print(f"   ⏰ Tempo limite atingido!")
                break
                
            result = future.result()
            if result:
                found_pin = result
                break
            pins_tested += CHUNK_SIZE
    
    elapsed = time.perf_counter() - start_time
    
    return AttackResult(num_processes, found_pin, elapsed, pins_tested, time_limit)

def generate_report(results: List[AttackResult], target_hash: str, found_pin: Optional[str]):
    """Gera planilha Excel com análises e gráficos"""
    
    print("\n📊 Gerando relatório com pandas...")
    
    # Prepara os dados
    data = []
    base_time = None
    
    for i, r in enumerate(results):
        # Calcula speedup (baseado no primeiro resultado com 1 processo)
        if r.processes == 1:
            base_time = r.time
            speedup = 1.0
            efficiency = 1.0
        else:
            if base_time:
                speedup = base_time / r.time if r.time > 0 else 0
                efficiency = speedup / r.processes
            else:
                speedup = 0
                efficiency = 0
        
        data.append({
            'Processos': r.processes,
            'Tempo_Limite(s)': r.time_limit,
            'Tempo_Real(s)': round(r.time, 4),
            'PINs_Testados': r.pins_tested,
            'PINs_por_Segundo': round(r.pins_per_second, 0),
            'Speedup': round(speedup, 3),
            'Eficiência': round(efficiency, 3),
            'Percentual_Testado': round((r.pins_tested / MAX_N) * 100, 4)
        })
    
    # Cria DataFrame
    df = pd.DataFrame(data)
    
    # Adiciona info do PIN encontrado
    if found_pin:
        df['PIN_Encontrado'] = found_pin
        df['Hash_Alvo'] = target_hash
    
    # Salva Excel
    excel_file = 'relatorio_quebra_hash.xlsx'
    with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
        # Aba de dados
        df.to_excel(writer, sheet_name='Dados', index=False)
        
        # Aba de análise
        analysis = pd.DataFrame({
            'Métrica': ['Hash Alvo', 'PIN Encontrado', 'Total Combinações', 
                       'Chunk Size', 'Tempo Total', 'Melhor Performance'],
            'Valor': [
                target_hash,
                found_pin if found_pin else 'NÃO ENCONTRADO',
                f"{MAX_N:,}",
                f"{CHUNK_SIZE:,}",
                f"{sum(r.time for r in results):.2f}s",
                f"{max(df['PINs_por_Segundo']):,.0f} PINs/s"
            ]
        })
        analysis.to_excel(writer, sheet_name='Análise', index=False)
        
        # Cria gráficos
        if len(data) > 1:
            fig, axes = plt.subplots(2, 2, figsize=(12, 10))
            
            # Gráfico 1: Tempo vs Processos
            axes[0, 0].plot(df['Processos'], df['Tempo_Real(s)'], 'bo-', linewidth=2, markersize=8)
            axes[0, 0].set_xlabel('Número de Processos')
            axes[0, 0].set_ylabel('Tempo (segundos)')
            axes[0, 0].set_title('Tempo de Execução vs Processos')
            axes[0, 0].grid(True, alpha=0.3)
            
            # Gráfico 2: Speedup
            axes[0, 1].plot(df['Processos'], df['Speedup'], 'ro-', linewidth=2, markersize=8)
            axes[0, 1].plot(df['Processos'], df['Processos'], 'k--', alpha=0.5, label='Speedup Ideal')
            axes[0, 1].set_xlabel('Número de Processos')
            axes[0, 1].set_ylabel('Speedup')
            axes[0, 1].set_title('Speedup vs Processos')
            axes[0, 1].legend()
            axes[0, 1].grid(True, alpha=0.3)
            
            # Gráfico 3: Eficiência
            axes[1, 0].bar(df['Processos'], df['Eficiência'], color='green', alpha=0.7)
            axes[1, 0].axhline(y=1.0, color='r', linestyle='--', alpha=0.5, label='Eficiência Ideal')
            axes[1, 0].set_xlabel('Número de Processos')
            axes[1, 0].set_ylabel('Eficiência')
            axes[1, 0].set_title('Eficiência do Paralelismo')
            axes[1, 0].legend()
            axes[1, 0].grid(True, alpha=0.3)
            
            # Gráfico 4: PINs por Segundo
            axes[1, 1].bar(df['Processos'], df['PINs_por_Segundo'], color='purple', alpha=0.7)
            axes[1, 1].set_xlabel('Número de Processos')
            axes[1, 1].set_ylabel('PINs/segundo')
            axes[1, 1].set_title('Performance (PINs por segundo)')
            axes[1, 1].grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            # Salva gráficos como imagem
            chart_file = 'graficos_analise.png'
            plt.savefig(chart_file, dpi=300, bbox_inches='tight')
            plt.close()
    
    print(f"   ✅ Relatório salvo: {excel_file}")
    if os.path.exists('graficos_analise.png'):
        print(f"   ✅ Gráficos salvos: graficos_analise.png")

def print_header():
    """Imprime cabeçalho principal"""
    clear_screen()
    print("=" * 70)
    print("🔐 QUEBRA DE HASH MD5 - PIN 9 DÍGITOS")
    print("=" * 70)
    print(f"🎯 Hash: {TARGET_HASH}")
    print(f"📊 Total: {MAX_N:,} combinações")
    print(f"📦 Chunk: {CHUNK_SIZE:,} PINs")
    print(f"💻 CPUs: {multiprocessing.cpu_count()}")
    print("=" * 70)
    print("\n📋 Estratégia: tempo limite decrescente com mais processos")
    print("-" * 70)

def print_progress_summary(results: List[AttackResult], total_pins: int):
    """Imprime resumo do progresso até agora"""
    clear_screen()
    print_header()
    
    print("\n📊 PROGRESSO DA BUSCA:")
    print("-" * 90)
    print(f"{'Proc':^6} | {'Tempo':^10} | {'PINs/s':^12} | {'Testado':^12} | {'%':^6} | {'Status':^10}")
    print("-" * 90)
    
    total_tested = 0
    for r in results:
        total_tested += r.pins_tested
        percent = (total_tested / MAX_N) * 100
        status = "✅" if r.found else "⏳"
        print(f"{r.processes:^6} | {r.time:^10.2f} | {r.pins_per_second:^12,.0f} | "
              f"{total_tested:^12,} | {percent:^6.2f}% | {status:^10}")
    
    print("-" * 90)

def main():
    results = []
    total_pins_tested = 0
    found_pin = None
    start_time = time.time()
    
    print_header()
    
    for procs, time_limit in PROCESS_CONFIGS:
        print(f"\n▶ Testando com {procs} processo(s) (limite: {time_limit}s)...")
        
        result = run_attack(TARGET_HASH, MAX_N, procs, time_limit)
        results.append(result)
        total_pins_tested += result.pins_tested
        
        # Mostra resultado atual
        percent = (total_pins_tested / MAX_N) * 100
        if result.found:
            found_pin = result.found
            print(f"\n🎉🎉🎉 SUCESSO! PIN: {result.found} 🎉🎉🎉")
            print(f"🔍 Hash: {hashlib.md5(result.found.encode()).hexdigest()}")
            break
        else:
            print(f"   → {percent:.2f}% testado até agora")
            print_progress_summary(results, total_pins_tested)
    
    elapsed = time.time() - start_time
    
    # Limpa tela para resultado final
    clear_screen()
    print_header()
    
    if found_pin:
        print("\n" + "=" * 70)
        print(f"🎉🎉🎉 SUCESSO! PIN ENCONTRADO: {found_pin} 🎉🎉🎉")
        print("=" * 70)
    else:
        print("\n" + "=" * 70)
        print("❌ HASH NÃO QUEBRADA")
        print("=" * 70)
        print(f"⏱️  Tempo total: {elapsed:.2f}s")
        print(f"🔢 PINs testados: {total_pins_tested:,} ({total_pins_tested/MAX_N*100:.2f}%)")
    
    # Gera relatório
    generate_report(results, TARGET_HASH, found_pin)
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()