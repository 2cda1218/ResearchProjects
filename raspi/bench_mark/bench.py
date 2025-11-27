import time
import math

def bench(name,func,repeat=1):
    start = time.perf_counter()
    for _ in range(repeat):
        func()
    end = time.perf_counter()
    duration = end - start
    print(f'{name}: {duration:.4f} sec')
    return duration

# CPU:素数
def prime_test(limit=20000):
    primes = []
    for n in range(2,limit):
        is_prime = True
        for i in range(2, int(n**0.5)+1):
            if n % i == 0:
                is_prime = False
                break
        if is_prime:
            primes.append(n)

# 浮動小数点:三角関数
def math_test(count=2_000_000):
    total = 0.0
    for i in range(1,count):
        total += math.sin(i) * math.cos(i)
    return total

# メモリ:操作
def memory_test(size=5_000_000):
    data = list(range(size))
    data.reverse()
    data.sort()

def main():
    print("----------ベンチマークスタート----------")
    bench("素数",prime_test,repeat=1)
    bench("浮動小数",math_test,repeat=1)
    bench("メモリ操作",memory_test,repeat=1)
    print("----------終了----------")

if __name__ == "__main__":
    main()