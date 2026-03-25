from psychopy import visual, core, event, sound, gui
import numpy as np
import random
import csv
from datetime import datetime

# --- 0. START SKÆRM (DIALOG BOKS TIL ID) ---
exp_info = {'Participant ID': ''}
dlg = gui.DlgFromDict(dictionary=exp_info, sortKeys=False, title="Pilot Forsøg")

if not dlg.OK:
    print("Forsøg afbrudt af brugeren.")
    core.quit()

participant_id = exp_info['Participant ID']

# --- 1. OPSÆTNING AF VINDUE OG STIMULI ---
win = visual.Window(fullscr=True, color='white', units='height')

fixation = visual.TextStim(win, text='+', color='black', height=0.05)
vis_standard = visual.Circle(win, radius=0.15, fillColor='black')
vis_deviant = visual.Circle(win, radius=0.3, fillColor='black')

aud_standard = sound.Sound(value=440, secs=0.3)
aud_deviant = sound.Sound(value=880, secs=0.3)

# --- 2. LOGIK TIL SEKVENSER ---
states = ['ss', 'av', 'sv', 'as']
n_trials_per_block = 50 # Fast antal trials for alle 24 blokke

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

# --- 3. BLOK OPSÆTNING OG RANDOMISERING ---
# Vi ganger listerne med det antal gange de skal gentages!
blocks_single = [
    {'type': 'static', 'deviants': ['av']},
    {'type': 'static', 'deviants': ['sv']},
    {'type': 'static', 'deviants': ['as']},
    {'type': 'dynamic', 'deviants': ['av']},
    {'type': 'dynamic', 'deviants': ['sv']},
    {'type': 'dynamic', 'deviants': ['as']}
] * 2  # Bliver til 12 blokke i alt

blocks_mixed = [
    {'type': 'static', 'deviants': ['av', 'sv', 'as']},
    {'type': 'dynamic', 'deviants': ['av', 'sv', 'as']}
] * 6  # Bliver til 12 blokke i alt

# Randomiser de to lister hver for sig
random.shuffle(blocks_single)
random.shuffle(blocks_mixed)

# Sæt dem sammen så de 12 single-blokke kommer først, 
# efterfulgt af de 12 mixed-blokke (i alt 24 blokke)
all_block_configs = blocks_single + blocks_mixed

blocks = []
for i, config in enumerate(all_block_configs):
    if config['type'] == 'static':
        seq = generate_static_sequence(n_trials_per_block, config['deviants'])
    else:
        seq = generate_dynamic_sequence(n_trials_per_block, config['deviants'])
    
    # Teksten på skærmen opdateret til 'AF 24'
    inst_text = f"BLOK {i+1} AF 24\n\nGæt næste hændelse!\nTryk 's' for Standard\nTryk 'k' for Deviant\n\nTryk på MELLEMRUM for at starte."
    instruction = visual.TextStim(win, text=inst_text, color='black', height=0.05)
    
    blocks.append({
        'block_num': i + 1,
        'type': config['type'],
        'deviants': config['deviants'],
        'sequence': seq,
        'instruction': instruction
    })

# --- 4. KØRSEL AF EKSPERIMENTET ---
eksperiment_data = []
trial_clock = core.Clock()

for block in blocks:
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
        rt = trial_clock.getTime() if keys else None
        
        is_deviant_trial = state in ['av', 'sv', 'as']
        predicted_deviant = response == 'k'
        correct = (is_deviant_trial and predicted_deviant) or (not is_deviant_trial and not predicted_deviant)

        if state == 'ss':
            vis_standard.draw()
            aud_standard.play()
        elif state == 'sv':
            vis_deviant.draw()
            aud_standard.play()
        elif state == 'as':
            vis_standard.draw()
            aud_deviant.play()
        elif state == 'av':
            vis_deviant.draw()
            aud_deviant.play()
            
        win.flip()
        core.wait(1.0) 
        
        eksperiment_data.append({
            'participant_id': participant_id,
            'block_num': block['block_num'],
            'dynamic': block['type'] == 'dynamic', 
            'av': 'av' in block['deviants'],       
            'sv': 'sv' in block['deviants'],       
            'as': 'as' in block['deviants'],       
            'trial': trial_num + 1,
            'state': state,
            'response': response,
            'rt': rt,
            'correct': correct
        })

# --- 5. AFSLUTNING OG DATA GEM ---
win.close()

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
filename = f"pilot_data_{participant_id}_{timestamp}.csv"

fieldnames = ['participant_id', 'block_num', 'dynamic', 'av', 'sv', 'as', 'trial', 'state', 'response', 'rt', 'correct']

with open(filename, mode='w', newline='', encoding='utf-8') as file:
    writer = csv.DictWriter(file, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(eksperiment_data)

print(f"\n--- DATA GEMT ---")
print(f"Al data er gemt i filen: {filename}\n")

print("--- PILOT RESULTATER Opsummering ---")
for block in blocks:
    b_num = block['block_num']
    block_data = [d for d in eksperiment_data if d['block_num'] == b_num]
    correct_trials = sum([1 for d in block_data if d['correct']])
    accuracy = (correct_trials / len(block_data)) * 100
    
    b_type = "Dynamisk" if block['type'] == 'dynamic' else "Statisk "
    b_devs = ", ".join(block['deviants']).upper()
    print(f"Blok {b_num:02d} | {b_type} [{b_devs:^10}]: Accuracy = {accuracy:.2f}%")