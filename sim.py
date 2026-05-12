import random
import math
import statistics

def calc_entropy(seq):
    """
    Beregner den overordnede (globale) frekvens og Shannon entropi 
    for en given sekvens af standarder og afvigere.
    """
    counts = {'standard': 0, 'deviant': 0}
    for s in seq:
        counts[s] += 1
    
    # Udregn sandsynlighederne (procenterne)
    p_std = counts['standard'] / len(seq)
    p_dev = counts['deviant'] / len(seq)
    
    # Undgå "math domain error" ved log2(0), hvis en af dem (mod forventning) er 0%
    if p_std == 0 or p_dev == 0:
        return p_std, p_dev, 0.0
        
    # Shannons formel for entropi: H = - sum( p * log2(p) )
    entropy = -(p_std * math.log2(p_std) + p_dev * math.log2(p_dev))
    
    return p_std, p_dev, entropy

def calc_cumulative_entropies(seq):
    """
    Beregner den løbende (kumulative) entropi op til og med hver enkelt trial.
    Returnerer en liste med entropien ved trial 1, trial 2, ..., trial N.
    """
    entropies = []
    counts = {'standard': 0, 'deviant': 0}
    for i, s in enumerate(seq):
        counts[s] += 1
        n = i + 1
        p_std = counts['standard'] / n
        p_dev = counts['deviant'] / n
        
        if p_std == 0 or p_dev == 0:
            entropies.append(0.0)
        else:
            ent = -(p_std * math.log2(p_std) + p_dev * math.log2(p_dev))
            entropies.append(ent)
            
    return entropies


# Antal trials vi vil simulere (1 million for at lade the Law of Large Numbers udjævne alt støj)
N = 1_000 

# ==========================================
# 1. STATISK BLOK SIMULATION (Flat 85/15)
# ==========================================
static_seq = []

for _ in range(N):
    # Kast en "terning" mellem 0.0 og 1.0. Hvis den er under 0.15 (15%), er det en afviger.
    if random.random() < 0.15:
        static_seq.append('deviant')
    else:
        static_seq.append('standard')


# ==========================================
# 2. DYNAMISK BLOK SIMULATION (Hazard Rate)
# ==========================================
dynamic_seq = []
run_length = 0 # Holder styr på, hvor mange standarder vi har haft i træk

for _ in range(N):
    # Udregn den lokale sandsynlighed baseret på foregående standarder i træk
    if run_length < 3:
        p_deviant = 0.00
    elif run_length == 3:
        p_deviant = 0.10
    elif run_length == 4:
        p_deviant = 0.15
    elif run_length == 5:
        p_deviant = 0.25
    elif run_length == 6:
        p_deviant = 0.50
    else:
        p_deviant = 1.00 # Efter 7 eller flere standarder tvinges en afviger frem
        
    # Kast "terningen" ud fra den aktuelle hazard rate
    if random.random() < p_deviant:
        dynamic_seq.append('deviant')
        run_length = 0 # Nulstil tælleren, fordi mønsteret blev brudt
    else:
        dynamic_seq.append('standard')
        run_length += 1 # Læg 1 til tælleren


# ==========================================
# 3. BEREGN OG UDSKRIV RESULTATER
# ==========================================
s_p_std, s_p_dev, s_ent = calc_entropy(static_seq)
d_p_std, d_p_dev, d_ent = calc_entropy(dynamic_seq)

s_cum_ents = calc_cumulative_entropies(static_seq)
d_cum_ents = calc_cumulative_entropies(dynamic_seq)

s_median = statistics.median(s_cum_ents)
s_stdev = statistics.stdev(s_cum_ents)

d_median = statistics.median(d_cum_ents)
d_stdev = statistics.stdev(d_cum_ents)

print(f"--- STATISK BLOK (N={N}) ---")
print(f"Standard frekvens: {s_p_std*100:.2f}%")
print(f"Afviger frekvens:  {s_p_dev*100:.2f}%")
print(f"Samlet Entropi:    {s_ent:.4f} bits")
print(f"Løbende Entropi Median: {s_median:.4f} bits")
print(f"Løbende Entropi Std:    {s_stdev:.4f} bits\n")

print(f"--- DYNAMISK BLOK (N={N}) ---")
print(f"Standard frekvens: {d_p_std*100:.2f}%")
print(f"Afviger frekvens:  {d_p_dev*100:.2f}%")
print(f"Samlet Entropi:    {d_ent:.4f} bits")
print(f"Løbende Entropi Median: {d_median:.4f} bits")
print(f"Løbende Entropi Std:    {d_stdev:.4f} bits")