from psychopy import prefs
prefs.hardware['audioLib'] = ['PTB', 'sounddevice', 'pygame']
prefs.hardware['audioSampleRate'] = 44100
from psychopy import visual, core, event, sound, gui
import numpy as np
import random
import csv
from datetime import datetime
import os

# --- 1. OPSÆTNING AF VINDUE OG STIMULI ---
win = visual.Window(fullscr=True, color='white', units='height')

fixation = visual.TextStim(win, text='+', color='black', height=0.05)
vis_standard = visual.Circle(win, radius=0.15, fillColor='black')
vis_deviant = visual.Circle(win, radius=0.3, fillColor='black')

aud_standard = sound.Sound(value=440, secs=0.3, sampleRate=44100)
aud_deviant = sound.Sound(value=880, secs=0.3, sampleRate=44100)

# Generel velkomst og forklaring af forsøget
velkomst_tekst = (
    "VELKOMMEN TIL EKSPERIMENTET!\n\n"
    "I dette forsøg undersøger vi, hvordan hjernen opfatter og forudsiger mønstre i lyd og billede.\n\n"
    "Du vil blive præsenteret for en række visuelle figurer og toner. "
    "Nogle gange vil de følge et fast 'Standard' mønster, og andre gange vil der forekomme en 'Afvigelse'.\n\n"
    "Din opgave er at prøve at forudsige, om der kommer en 'Standard' eller en 'Afvigende' hændelse som det næste.\n\n"
    "Tryk på MELLEMRUM for at læse instruktionerne til opgaven."
)
velkomst_skærm = visual.TextStim(win, text=velkomst_tekst, color='black', height=0.04, wrapWidth=1.2)


# --- 2. LOGIK TIL SEKVENSER ---
states = ['ss', 'av', 'sv', 'as']
n_trials_per_block = 10 # Kort antal trials til øvelsen

def generate_static_sequence(n_trials, allowed_deviants):
    seq = []
    current = 'ss'
    for _ in range(n_trials):
        probs = [0.0, 0.0, 0.0, 0.0]
        
        if current == 'ss':
            p_stay = 0.50
            p_change = 0.50
            probs[0] = p_stay
            
            for dev in allowed_deviants:
                idx = states.index(dev)
                probs[idx] = p_change / len(allowed_deviants)
        else:
            probs[0] = 1.0 
            
        next_state = np.random.choice(states, p=probs)
        seq.append(next_state)
        current = next_state
        
    return seq

def generate_dynamic_sequence(n_trials, allowed_deviants):
    seq = []
    current = 'ss'
    streak = 0
    
    for _ in range(n_trials):
        streak += 1
        probs = [0.0, 0.0, 0.0, 0.0]
        
        if current == 'ss':
            change_probs = [0.40, 0.60, 0.80, 0.99]
            idx = min(streak - 1, 3) 
            p_change = change_probs[idx]
            p_stay = 1.0 - p_change
            
            probs[0] = p_stay
            for dev in allowed_deviants:
                idx_state = states.index(dev)
                probs[idx_state] = p_change / len(allowed_deviants)
            
        else: 
            change_probs = [0.80, 0.99]
            idx = min(streak - 1, 1)
            p_change = change_probs[idx]
            p_stay = 1.0 - p_change
            
            for i, s in enumerate(states):
                if s == current:
                    probs[i] = p_stay 
                elif s == 'ss':
                    probs[i] = p_change 
                else:
                    probs[i] = 0.0
                    
        next_state = np.random.choice(states, p=probs)
        seq.append(next_state)
        
        if next_state != current:
            streak = 0
            
        current = next_state
        
    return seq

# --- 3. BLOK OPSÆTNING ---
# 4 specifikke blokke: SV, AS, AV, og Mix. Skifter mellem statisk og dynamisk.
practice_configs = [
    {'type': 'static',  'deviants': ['sv']},             # 1. Kun SV (Statisk)
    {'type': 'dynamic', 'deviants': ['as']},             # 2. Kun AS (Dynamisk)
    {'type': 'static',  'deviants': ['av']},             # 3. Kun AV (Statisk)
    {'type': 'dynamic', 'deviants': ['av', 'sv', 'as']}  # 4. Mikset (Dynamisk)
]

blocks = []
for i, config in enumerate(practice_configs):
    if config['type'] == 'static':
        seq = generate_static_sequence(n_trials_per_block, config['deviants'])
    else:
        seq = generate_dynamic_sequence(n_trials_per_block, config['deviants'])
    
    inst_text = f"ØVELSE: BLOK {i+1} AF 4\n\nGæt næste hændelse!\nTryk 's' for Standard\nTryk 'k' for Afvinde\n\nTryk på MELLEMRUM for at starte."
    instruction = visual.TextStim(win, text=inst_text, color='black', height=0.05)
    
    blocks.append({
        'block_num': i + 1,
        'type': config['type'],
        'deviants': config['deviants'],
        'sequence': seq,
        'instruction': instruction
    })

# --- 4. KØRSEL AF ØVELSEN ---
# Vis den overordnede velkomstskærm først
velkomst_skærm.draw()
win.flip()
event.waitKeys(keyList=['space', 'escape'])

eksperiment_data = [] 
trial_clock = core.Clock()

for block in blocks:
    # Herefter vises instruktionen for den specifikke blok
    block['instruction'].draw()
    win.flip()
    event.waitKeys(keyList=['space'])
    
    for trial_num, state in enumerate(block['sequence']):
        fixation.draw()
        win.flip()
        
        trial_clock.reset()
        keys = event.waitKeys(keyList=['s', 'k', 'escape'])
        
        if keys and 'escape' in keys:
            win.close()
            core.quit()
            
        response = keys[0] if keys else 'None'
        
        is_deviant_trial = state in ['av', 'sv', 'as']
        predicted_deviant = response == 'k'
        correct = (is_deviant_trial and predicted_deviant) or (not is_deviant_trial and not predicted_deviant)

        if state == 'ss':
            vis_standard.draw()
            aud_standard.stop()
            aud_standard.play()
        elif state == 'sv':
            vis_deviant.draw()
            aud_standard.stop()
            aud_standard.play()
        elif state == 'as':
            vis_standard.draw()
            aud_deviant.stop()
            aud_deviant.play()
        elif state == 'av':
            vis_deviant.draw()
            aud_deviant.stop()
            aud_deviant.play()
            
        win.flip()
        core.wait(1.0) 
        
        eksperiment_data.append({
            'block_num': block['block_num'],
            'correct': correct
        })

# --- 5. AFSLUTNING UDEN GEMNING ---
win.close()

print("\n--- ØVELSE AFSLUTTET ---")
print("Data er IKKE gemt som fil.\n")
for block in blocks:
    b_num = block['block_num']
    block_data = [d for d in eksperiment_data if d['block_num'] == b_num]
    correct_trials = sum([1 for d in block_data if d['correct']])
    accuracy = (correct_trials / len(block_data)) * 100
    
    b_type = "Dynamisk" if block['type'] == 'dynamic' else "Statisk "
    b_devs = ", ".join(block['deviants']).upper()
    print(f"Øvelsesblok {b_num} | {b_type} [{b_devs:^10}]: Accuracy = {accuracy:.2f}%")