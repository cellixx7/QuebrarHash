import hashlib
import itertools
import string
import multiprocessing
import time

# Alvo da nossa busca
TARGET_HASH = "ca6ae33116b93e57b87810a27296fc36"

# Conjunto de caracteres permitidos (apenas dígitos)
CHARSET = string.digits

def escolher_workers():
    """
    Função para o usuário definir quantos processos paralelos serão utilizados.
    """
    total_cpus = multiprocessing.cpu_count()
    print(f"⚡ Este sistema possui {total_cpus} núcleos de processamento disponíveis.")
    
    opcao = input(f"▶ Quantos núcleos deseja alocar para o ataque? (ENTER para usar todos os {total_cpus}): ")
    
    if opcao.strip() == "":
        return total_cpus
    
    try:
        quantidade = int(opcao)
        if 1 <= quantidade <= total_cpus:
            return quantidade
        elif quantidade > total_cpus:
            print(f"⚠️ Valor excede o máximo disponível. Utilizando {total_cpus} núcleos.")
            return total_cpus
        else:
            print(f"⚠️ Valor inválido. Utilizando 1 núcleo.")
            return 1
    except ValueError:
        print(f"⚠️ Entrada não reconhecida. Utilizando {total_cpus} núcleos.")
        return total_cpus

def verificar_combinacao(params):
    """
    Função executada por cada processo:
    Recebe um prefixo e o comprimento total da senha.
    Exemplo: ('12', 4) testa de '1200' até '1299'
    """
    prefixo, comprimento_total = params
    chars_restantes = comprimento_total - len(prefixo)
    
    for sufixo in itertools.product(CHARSET, repeat=chars_restantes):
        tentativa = prefixo + "".join(sufixo)
        
        if hashlib.md5(tentativa.encode('utf-8')).hexdigest() == TARGET_HASH:
            return tentativa
            
    return None

if __name__ == '__main__':
    print("=" * 60)
    print("🔐 SISTEMA DE FORÇA BRUTA DISTRIBUÍDA")
    print("=" * 60)
    
    workers = escolher_workers()
    
    print(f"\n🚀 Iniciando ataque com {workers} processos paralelos...")
    inicio = time.time()
    encontrado = False

    # Testa comprimentos de 1 a 9 dígitos
    for comprimento in range(1, 10):
        print(f"📡 Verificando combinações de {comprimento} dígitos...")
        
        # Estratégia de divisão do trabalho
        if comprimento <= 2:
            # Para senhas curtas, não precisa dividir muito
            tarefas = [("", comprimento)]
        else:
            # Para senhas maiores, divide pelos primeiros 2 dígitos
            prefixos_iniciais = ["".join(p) for p in itertools.product(CHARSET, repeat=2)]
            tarefas = [(prefixo, comprimento) for prefixo in prefixos_iniciais]

        # Distribui as tarefas entre os processos
        with multiprocessing.Pool(processes=workers) as pool:
            for resultado in pool.imap_unordered(verificar_combinacao, tarefas):
                if resultado:
                    print("\n" + "⭐" * 30)
                    print("✅ HASH QUEBRADA COM SUCESSO!")
                    print(f"🔑 SENHA ENCONTRADA: {resultado}")
                    print("⭐" * 30 + "\n")
                    encontrado = True
                    pool.terminate()
                    break
        
        if encontrado:
            break
            
    tempo_total = round(time.time() - inicio, 2)
    
    if encontrado:
        print(f"⏱️  Tempo total de processamento: {tempo_total} segundos.")
    else:
        print(f"\n❌ Nenhuma correspondência encontrada para os comprimentos testados.")
        print(f"⏱️  Tempo total de processamento: {tempo_total} segundos.")
    
    print("=" * 60)