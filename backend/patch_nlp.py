import sys
content = open('ml_model.py', encoding='utf-8').read()
old_end = '    "cold intolerance": "cold_intolerance", "always cold": "cold_intolerance",\n}'
if old_end not in content:
    # Try with \r\n
    old_end = '    "cold intolerance": "cold_intolerance", "always cold": "cold_intolerance",\r\n}'

extra = '''
    "high fever": "high_fever", "mild fever": "mild_fever", "night sweats": "night_sweats",
    "excessive sweating": "excessive_sweating", "dry cough": "dry_cough",
    "cough with phlegm": "cough_with_phlegm", "coughing blood": "blood_in_sputum",
    "wheezing": "wheezing", "breathlessness": "breathlessness", "chest tightness": "chest_tightness",
    "runny nose": "runny_nose", "sneezing": "sneezing", "nasal congestion": "nasal_congestion",
    "stuffy nose": "nasal_congestion", "loss of smell": "loss_of_smell", "loss of taste": "loss_of_taste",
    "ear pain": "ear_pain", "yellow eyes": "yellow_eyes", "eye pain": "eye_pain", "itchy eyes": "itchy_eyes",
    "yellow skin": "yellow_skin", "jaundice": "yellow_skin", "scaly patches": "scaly_patches",
    "red patches": "red_patches", "rose spots": "rose_spots", "bleeding tendency": "bleeding_tendency",
    "bruising easily": "bleeding_tendency", "skin rash": "skin_rash",
    "severe joint pain": "severe_joint_pain", "body ache": "muscle_aches", "back pain": "back_pain",
    "lower back pain": "lower_back_pain", "flank pain": "flank_pain", "side pain": "flank_pain",
    "frequent urination": "frequent_urination", "urinating often": "frequent_urination",
    "peeing a lot": "frequent_urination", "polyuria": "polyuria",
    "burning urination": "burning_urination", "pain when urinating": "burning_urination",
    "cloudy urine": "cloudy_urine", "blood in urine": "blood_in_urine", "pelvic pain": "pelvic_pain",
    "vomiting": "vomiting", "vomit": "vomiting", "severe stomach pain": "severe_abdominal_pain",
    "right side pain": "lower_right_pain", "stomach cramps": "abdominal_cramps",
    "loose motions": "diarrhea", "watery stool": "watery_diarrhea", "constipation": "constipation",
    "dark urine": "dark_urine", "blood in stool": "blood_in_stool", "mucus in stool": "mucus_in_stool",
    "loss of appetite": "loss_of_appetite", "not eating": "loss_of_appetite", "dehydrated": "dehydration",
    "tremors": "tremors", "shaking hands": "tremors", "fits": "seizures", "convulsions": "seizures",
    "fainted": "loss_of_consciousness", "unconscious": "loss_of_consciousness",
    "confusion": "confusion", "forgetful": "memory_loss", "slow movement": "slow_movement",
    "muscle rigidity": "muscle_rigidity", "cold hands": "cold_hands", "cold feet": "cold_hands",
    "anxiety": "anxiety", "anxious": "anxiety", "panic attack": "panic_attacks",
    "restless": "restlessness", "mood swings": "mood_swings",
    "palpitations": "palpitations", "heart racing": "rapid_heartbeat",
    "radiating arm pain": "radiating_arm_pain", "heat intolerance": "heat_intolerance",
    "loud snoring": "loud_snoring", "snoring": "loud_snoring",
    "gasping in sleep": "gasping_during_sleep", "swollen glands": "swollen_lymph_nodes",
    "foot swelling": "hand_foot_swelling", "ankle swelling": "hand_foot_swelling",
    "weight gain": "weight_gain", "gaining weight": "weight_gain", "tummy ache": "abdominal_pain",
    "body pain": "muscle_aches", "tummy pain": "abdominal_pain",
}'''

new_end = '    "cold intolerance": "cold_intolerance", "always cold": "cold_intolerance",' + extra

if old_end in content:
    content = content.replace(old_end, new_end)
    open('ml_model.py', 'w', encoding='utf-8').write(content)
    print('SUCCESS: NLP map expanded with', extra.count(':'), 'new entries')
else:
    # Find approximate location
    idx = content.find('cold_intolerance')
    print(f'FAIL: old_end not found. cold_intolerance appears at chars: {[i for i in range(len(content)) if content[i:].startswith("cold_intolerance")][:5]}')
    print('Context around last occurrence:', repr(content[max(0,idx-20):idx+80]))
