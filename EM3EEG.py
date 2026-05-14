import matplotlib.pyplot as plt
import numpy as np
import mne
from mne.preprocessing import ICA
import pandas as pd
import seaborn as sns

# Stier
bdf_path = r"C:/Users/lundb/OneDrive/Skrivebord/KU/4. Semester/EM3/Projekt/LuChris_1.bdf"
csv_path = r"C:/Users/lundb/OneDrive/Skrivebord/KU/4. Semester/EM3/Projekt/data_p9876_20260508_1018.csv"

# Indlæsning af data
raw = mne.io.read_raw_bdf(bdf_path, preload=True)   # .bdf
raw.resample(250)
raw.set_eeg_reference('average', projection=False)  
df = pd.read_csv(csv_path)                          # .csv

# raw.set_montage('standard_1020')

# ICA (Independent Component Analysis) For at fjerne øjenblink
raw_ica = raw.copy().filter(l_freq=1.0, h_freq=30.0)
ica = mne.preprocessing.ICA(n_components=20, random_state=42, max_iter='auto')
ica.fit(raw_ica, decim=3)

# Bed MNE om automatisk at finde blink vha. de forreste elektroder. 
eog_channels = ['Fp1', 'Fp2', 'Fpz'] 
try:
    eog_indices, eog_scores = ica.find_bads_eog(raw, ch_name=eog_channels)
    print(f"ICA fandt blink i komponent(er): {eog_indices}")
    ica.exclude = eog_indices
except Exception as e:
    print(f"Kunne ikke finde EOG automatisk (tjek elektrodenavne). Kør ica.plot_components(raw) for at vælge manuelt.")

# Filtrer den RIGTIGE data til ERP-brug (0.1 - 30 Hz) og træk blink-komponenterne ud
raw_clean = raw.copy().filter(l_freq=0.1, h_freq=30.0)
ica.apply(raw_clean)

# Find triggers
events = mne.find_events(raw_clean, stim_channel='Status')

# Sikkerhedstjek: Antal triggers fra EEG skal matche antal trials i CSV
if len(events) > len(df):
    print("Fandt ekstra start/stop triggers i EEG'et. Fjerner dem for at matche CSV...")
    events = events[-len(df):]

tmin, tmax = -0.2, 0.8
reject_criteria = dict(eeg=150e-6)

epochs = mne.Epochs(
    raw_clean, 
    events,
    metadata = df, 
    #event_id=event_dict, 
    tmin=tmin, 
    tmax=tmax, 
    baseline=(tmin, 0), # Nulstil baseline (-0.2 til 0) så alle starter samme sted
    preload=True,
    reject=reject_criteria
)

# Hvilke epochs der er droppet efter ICA
print(epochs.drop_log_stats())

blocks_to_exclude = [1,2,3,4,5,6,7,11,15,19,23,27]
epochs_main = epochs[f"block_num not in {blocks_to_exclude}"]
epochs_correct = epochs_main["correct == True"]
print(f"Beholder {len(epochs_correct)} trials til selve ERP analysen.")

# ==========================================
# 7. BEREGN OG PLOT FOR ALLE DEVIANT TYPER
# ==========================================
print("\nBeregner ERP'er for alle afvigertyper...")

# Standard baseline er den samme for alle (Kig kun på standard stimuli)
cond_standard = epochs_correct["stimulus_state == 'standard'"].average()

# Vi sætter en ordbog op, der fortæller Python præcis hvilke elektroder 
# der er bedst at kigge på for de forskellige sanser.
deviant_configs = {
    'AS': {
        'name': 'Auditory Deviant (Lyd)',
        'channels': ['Fz', 'Cz'] # Fz til aMMN, Cz til P300
    },
    'SV': {
        'name': 'Visual Deviant (Syn)',
        'channels': ['Oz', 'Pz'] # Oz til vMMN, Pz til P300
    },
    'AV': {
        'name': 'Multimodal Deviant (Lyd+Syn)',
        'channels': ['Fz', 'Oz', 'Pz'] # Fz/Oz til MMN'er, Pz til P300
    }
}

# Loop igennem de tre typer: AS, SV, AV
for dev_type, config in deviant_configs.items():
    print(f"\nGenererer plots for {config['name']}...")
    
    # Filtrer data for Statisk og Dynamisk for netop denne deviant
    cond_static = epochs_correct[f"block_type == 'Static' and deviant_type == '{dev_type}' and stimulus_state == 'deviant'"].average()
    cond_dynamic = epochs_correct[f"block_type == 'Dynamic' and deviant_type == '{dev_type}' and stimulus_state == 'deviant'"].average()
    
    # Saml dem til plottet
    evokeds_dict = {
        'Standard Baseline': cond_standard,
        f'{dev_type} (Static)': cond_static,
        f'{dev_type} (Dynamic)': cond_dynamic
    }
    
    # Farver til graferne
    colors = {
        'Standard Baseline': 'black', 
        f'{dev_type} (Static)': 'blue', 
        f'{dev_type} (Dynamic)': 'red'
    }
    
    # Plot kun de elektroder, der giver mening for denne sans
    for ch in config['channels']:
        # Tjek om elektroden findes i dataen (BioSemi 64 har f.eks. 'Oz')
        if ch in epochs_correct.ch_names:
            fig, ax = plt.subplots(figsize=(10, 6))
            mne.viz.plot_compare_evokeds(
                evokeds_dict,
                picks=[ch], 
                colors=colors,
                axes=ax,
                title=f"{config['name']} - Elektrode: {ch}",
                show_sensors=False
            )
            
            # Fremhæv MMN og P300 zonerne for at gøre det nemt at aflæse
            ax.axvspan(0.100, 0.250, color='gray', alpha=0.2, label='MMN Vindue (100-250ms)')
            ax.axvspan(0.300, 0.500, color='yellow', alpha=0.2, label='P300 Vindue (300-500ms)')
            ax.legend(loc='lower left')
            plt.show()
        else:
            print(f"ADVARSEL: Elektroden '{ch}' findes ikke i jeres BioSemi data.")
            
# ==========================================
# 8. TJEK ANTAL DEVIANTS (STATISK VS DYNAMISK)
# ==========================================
print("\nBeregner antal faktiske afvigere i dataen for alle betingelser...")

# Træk den underliggende pandas DataFrame ud fra vores rensede epochs
df_main = epochs_main.metadata

# Filtrer, så vi KUN kigger på trials, der faktisk var deviants
df_deviants = df_main[df_main['stimulus_state'] == 'deviant']

# Tæl hvor mange der er af hver kombination (block_type x deviant_type)
counts = df_deviants.groupby(['block_type', 'deviant_type']).size().reset_index(name='Antal')

# Print de rå tal i konsollen (Rigtig godt til metodeafsnittet!)
print("\n--- FAKTISK ANTAL DEVIANTS I DATAEN ---")
print(counts.to_string(index=False))

# Lav et flot grupperet bar-plot
plt.figure(figsize=(10, 6))

# Brug 'hue' til at farvekode Statisk/Dynamisk og 'x' til at dele op i AV, SV, AS
sns.barplot(
    data=counts, 
    x='deviant_type', 
    y='Antal', 
    hue='block_type', 
    palette={'Static': 'blue', 'Dynamic': 'red'}
)

plt.title('Antal Faktiske Afvigere pr. Betingelse\n(Efter rensning for blink og fejl)')
plt.ylabel('Antal Deviants (trials)')
plt.xlabel('Deviant Type')

# Sæt y-aksen til at starte ved 0 og give lidt luft i toppen
plt.ylim(0, max(counts['Antal']) * 1.2) 

# Gør 'legend' (signaturforklaringen) pænere
plt.legend(title='Betingelse', loc='lower right')

plt.tight_layout()
plt.show()

# ==========================================
# 9. MARKOV KÆDER: HAZARD RATE PÅ P300
# ==========================================
import copy

# 1. Frasorter fejl-trials først! (Guldstandard)
epochs_correct = epochs_main["correct == True"]

# 2. Hent metadataen for at tilføje vores tæller
m = epochs_correct.metadata.copy()

# 3. Kør igennem alle trials og tæl hvor mange standarder, der har været i træk
run_lengths = []
current_run = 0

for state in m['stimulus_state']:
    if state == 'standard':
        current_run += 1
        run_lengths.append(current_run)
    else: # Hvis det er en deviant
        # Gem hvor mange standarder der kom LIGE FØR denne deviant
        run_lengths.append(current_run) 
        current_run = 0 # Nulstil tælleren

# Tilføj den nye kolonne til vores metadata
m['run_length'] = run_lengths
epochs_correct.metadata = m

# ==========================================
# PLOT: TIDLIG VS SEN AFVIGER (Kun Dynamiske Blokke)
# ==========================================
print("\nBeregner ERP for Hazard Rate (Tidlig vs Sen Afviger)...")

# Vi kigger kun på 'AV' (Multimodal) i de Dynamiske blokke, da det ofte giver det klareste P300
# Du kan ændre 'AV' til 'SV' eller 'AS'
valgt_afviger = 'AV'

# "Tidlige" afvigere: Kom efter kun 3 eller 4 standarder (Høj surprisal / stor overraskelse)
cond_early = epochs_correct[f"block_type == 'Dynamic' and deviant_type == '{valgt_afviger}' and stimulus_state == 'deviant' and run_length <= 4"].average()

# "Sene" afvigere: Kom efter 6 eller flere standarder (Lav surprisal / forventet)
cond_late = epochs_correct[f"block_type == 'Dynamic' and deviant_type == '{valgt_afviger}' and stimulus_state == 'deviant' and run_length >= 6"].average()

# Den sorte baseline til sammenligning
cond_standard = epochs_correct["stimulus_state == 'standard'"].average()

evokeds_hazard = {
    'Standard Baseline': cond_standard,
    'Tidlig Afviger (Efter 3-4 std)': cond_early,
    'Sen Afviger (Efter 6+ std)': cond_late
}

colors = {
    'Standard Baseline': 'black', 
    'Tidlig Afviger (Efter 3-4 std)': 'orange', 
    'Sen Afviger (Efter 6+ std)': 'green'
}

# Plot Pz for P300
fig, ax = plt.subplots(figsize=(10, 6))
mne.viz.plot_compare_evokeds(
    evokeds_hazard,
    picks=['Pz'], 
    colors=colors,
    axes=ax,
    title=f'Hazard Rate Effekt på P300 ({valgt_afviger} Deviant, Elektrode Pz)',
    show_sensors=False
)

ax.axvspan(0.300, 0.500, color='yellow', alpha=0.2, label='P300 Vindue')
ax.legend(loc='lower left')
plt.show()