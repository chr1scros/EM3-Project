from psychopy import prefs
prefs.hardware['audioLib'] = ['pygame', 'sounddevice', 'PTB']
prefs.hardware['audioSampleRate'] = 44100
from psychopy import visual, core, event, sound, gui
import random
import os
import csv
import time

try:
    import serial
    port = serial.Serial("COM3", 115200) 
    eeg_connected = True
except Exception as e:
    eeg_connected = False
   
def send_trigger(code):
    """Sender trigger præcis når skærmen flipper"""
    if eeg_connected:
        try:
            port.write(code.to_bytes(1, 'big'))
        except Exception:
            pass

# Trigger Mapping
T_STANDARD = 1
T_AV_DEVIANT = 2
T_SV_DEVIANT = 3
T_AS_DEVIANT = 4

total_blocks = 30

static_prob = 0.85

exp_info = {'Forsøgsperson ID': ''}
dlg = gui.DlgFromDict(dictionary=exp_info, sortKeys=False, title="EM3 Eksperiment")
if not dlg.OK:
    core.quit() # Brugeren trykkede annuller
participant_id = exp_info['Forsøgsperson ID']

# Datafil
filename = f"data_p{participant_id}_{time.strftime('%Y%m%d_%H%M')}.csv"
with open(filename, 'w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(['participant_id', 'block_num', 'block_type', 'deviant_type', 
                     'trial_num', 'stimulus_state', 'trigger_code', 'response', 'rt', 'correct'])

# Skærm 
win = visual.Window(color='white', fullscr=True, units='height')
event.globalKeys.add(key='escape', func=core.quit)

# Pre-load Lyde og Billeder (Flash duration = 0.3 sekunder)
STIM_DURATION = 0.3
ISI_TOTAL = 2.0 # Total tid fra start af én trial til start af næste

aud_standard = sound.Sound(value=440, secs=STIM_DURATION, sampleRate=44100)
aud_deviant = sound.Sound(value=880, secs=STIM_DURATION, sampleRate=44100)

vis_standard = visual.Circle(win, radius=0.15, fillColor='black', lineColor='black')
vis_deviant = visual.Circle(win, radius=0.3, fillColor='black', lineColor='black')
fixation = visual.TextStim(win, text='+', color='black', height=0.1)

# Rækkefølge af blok-længder
block_lengths = [20, 60, 60, 60]

# Vi blander rækkefølgen af deviants
deviant_types = ['AV', 'AS', 'SV']
random.shuffle(deviant_types)

def generate_dynamic_trials(n_trials):
    """
    Genererer en dynamisk sekvens hvor sandsynligheden for en afviger 
    (Hazard Rate) stiger, jo flere standarder der har været i træk.
    Gennemsnittet lander på ca. 15% afvigere (0.61 bits entropi).
    """
    seq = []
    run_length = 0 # Tæller hvor mange standarder vi har haft i træk

    # Vi kører indtil blokken har det ønskede antal trials
    while len(seq) < n_trials:
        
        # Udregn sandsynligheden baseret på 'run_length'
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
            p_deviant = 1.00 # Efter 7 standarder SKAL den komme
            
        # Kast "terningen" ud fra den nye sandsynlighed
        if random.random() < p_deviant:
            seq.append('deviant')
            run_length = 0 # Nulstil tælleren
        else:
            seq.append('standard')
            run_length += 1
            
    # Skær arrayet præcis til n_trials (
    return seq[:n_trials]

def generate_trials(n_trials, prob_standard):
    """Genererer en sekvens baseret på sandsynligheden for en standard (Markov/Flat)"""
    seq = []
    for _ in range(n_trials):
        if random.random() < prob_standard:
            seq.append('standard')
        else:
            seq.append('deviant')
    return seq

block_counter = 1

# Instruktion
instructions = [
    "Velkommen til forsøget!\n\n"
    "I dette forsøg vil du opleve sekvenser af lyde og sekvenser af cirkler på skærmen.\n\n"
    "Tryk på MELLEMRUM for at læse videre.",
    
    "Inden vi starter, er det vigtigt at:\n\n"
    "1. Du sidder behageligt og kan hvile armene afslappet. Men altid have én hånd på mellemrums tasten.\n"
    "2. Du forsøger at lade være med at blinke, lige når stimuli vises.\n"
    "3. Du skal slappe af i skuldre, kæbe og nakke.\n\n"
    "Brug hellere end gerne pauserne mellem blokkene til at blinke og bevæge dit hovede alt det, du vil!\n\n"
    "Tryk på MELLEMRUM for at læse videre.",
    
    "OPGAVEN:\n\n"
    "Kig på fiksationskrydset (+) i midten af skærmen hele tiden.\n"
    "Størstedelen af det du ser og hører vil være 'standard' stimuli.\n"
    "Ind imellem vil der komme en 'afviger' (f.eks. en højere tone eller en større cirkel).\n\n"
    "Tryk på MELLEMRUM for at læse videre.",
    
    "Din opgave er at reagere på disse afvigere.\n\n"
    "Tryk KUN på MELLEMRUM, når du ser eller hører en afviger.\n"
    "Tryk så hurtigt du kan, men undlad at trykke ved standard stimuli.\n\n"
    "Tryk på MELLEMRUM, når du er klar til at starte forsøget."
]

for inst_text in instructions:
    inst = visual.TextStim(win, text=inst_text, color='black', height=0.04)
    inst.draw()
    win.flip()
    keys = event.waitKeys(keyList=['space', 'escape'])
    if keys and 'escape' in keys:
        core.quit()

trial_clock = core.Clock()

phases = [
    {'name': 'Training', 'lengths': [15], 'msg': "Nu starter træningsfasen.\n\nDu vil gennemgå 6 korte blokke (15 trials i hver) for at lære opgaven at kende.\n\nTryk på MELLEMRUM for at starte."},
    {'name': 'Experiment', 'lengths': block_lengths, 'msg': "Træningen er slut!\n\nNu starter selve forsøget.\n\nTryk på MELLEMRUM for at starte."}
]

for phase in phases:
    # Vis fase-instruktion
    phase_inst = visual.TextStim(win, text=phase['msg'], color='black', height=0.04)
    phase_inst.draw()
    win.flip()
    keys = event.waitKeys(keyList=['space', 'escape'])
    if keys and 'escape' in keys:
        core.quit()
        
    random.shuffle(deviant_types)
    
    for dev_type in deviant_types:
        
        # Kør først Statiske blokke, derefter Dynamiske blokke for denne deviant type
        for block_type in ['Static', 'Dynamic']:
            
            for b_length in phase['lengths']:
                current_block_type = f"Training_{block_type}" if phase['name'] == 'Training' else block_type
                
                if block_type == 'Static':
                    trials = generate_trials(b_length, static_prob) # Static
                else:
                    trials = generate_dynamic_trials(b_length) # Dynamic
                
                # Pause mellem blokke
                pause_msg = (
                    f"Blok {block_counter}/{total_blocks} er klar.\n\n"
                    "Tag en dyb indånding, blink alt det du har lyst til, og slap af i øjnene.\n\n"
                    "Der er ingen stress i pauserne - du styrer helt selv tempoet.\n"
                    "Når du er afslappet og klar igen, tryk på mellemrum for at fortsætte."
                )
                pause_text = visual.TextStim(win, text=pause_msg, color='black', height=0.04)
                pause_text.draw()
                win.flip()
                keys = event.waitKeys(keyList=['space', 'escape'])
                if keys and 'escape' in keys:
                    core.quit()
                
                # 2 sekunders forsinkelse (med fiksationskors) før første stimulus i blokken
                fixation.draw()
                win.flip()
                core.wait(2.0)
                
                trial_num = 1
                for trial in trials:
                    # Definer hvad der skal vises og spilles baseret på dev_type og trial
                    play_aud = aud_standard
                    show_vis = vis_standard
                    trig_code = T_STANDARD
                    is_deviant_trial = False
                    
                    if trial == 'deviant':
                        is_deviant_trial = True
                        if dev_type == 'AV':
                            play_aud = aud_deviant
                            show_vis = vis_deviant
                            trig_code = T_AV_DEVIANT
                        elif dev_type == 'AS':
                            play_aud = aud_deviant
                            show_vis = vis_standard
                            trig_code = T_AS_DEVIANT
                        elif dev_type == 'SV':
                            play_aud = aud_standard
                            show_vis = vis_deviant
                            trig_code = T_SV_DEVIANT
                    
                    # PRÆSENTATION AF STIMULUS
                    # Nulstil lyd og event-buffer
                    play_aud.stop() 
                    event.clearEvents()
                    trial_clock.reset()
                    
                    # Sæt triggeren til at fyre PRÆCIS når skærmen opdaterer
                    win.callOnFlip(send_trigger, trig_code)
                    
                    # Tegn stimulus
                    show_vis.draw()
                    fixation.draw()
                    win.flip()
                    
                    # Spil lyden
                    play_aud.play()
                    
                    # Sæt standardværdier
                    response = False
                    rt = 2.0000
                    stim_removed = False
                    
                    # Kør hele trial loopet
                    while trial_clock.getTime() < ISI_TOTAL:
                        # Fjern stimulus fra skærmen
                        if trial_clock.getTime() >= STIM_DURATION and not stim_removed:
                            fixation.draw()
                            win.flip()
                            stim_removed = True
                        
                        # Lyt efter input
                        keys = event.getKeys(keyList=['space', 'escape'], timeStamped=trial_clock)
                        if keys:
                            if keys[0][0] == 'escape':
                                core.quit()
                            elif response is False: 
                                response = True
                                rt = round(keys[0][1], 4)
                    
                    # Evaluering af svar
                    if is_deviant_trial and response is True:
                        correct = True
                    elif not is_deviant_trial and response is False:
                        correct = True
                    else:
                        correct = False
                    
                    # Gem data
                    with open(filename, 'a', newline='') as file:
                        writer = csv.writer(file)
                        writer.writerow([participant_id, block_counter, current_block_type, dev_type, 
                                         trial_num, trial, trig_code, response, rt, correct])
                    
                    trial_num += 1
                
                block_counter += 1

# Afslutning
end_text = visual.TextStim(win, text="Forsøget er slut.\n\nTak for din deltagelse!", color='black')
end_text.draw()
win.flip()
keys = event.waitKeys(keyList=['space', 'escape'])
if keys and 'escape' in keys:
    core.quit()
win.close()
core.quit()