"""Templated vocabulary for the 30,000 synthetic claim notes.

Each of the 12 condition categories has signature phrases (presentation /
exam / plan) plus a medication list. Designated category groups also draw
from a *shared confusable pool* -- vocabulary that legitimately overlaps
between related conditions (e.g. the orthopedic trio). That overlap is what
keeps the classifier honest instead of letting it memorize disjoint
keyword sets.

ALL TEXT IS SYNTHETIC. No real medical records are used or reproduced.
"""

from __future__ import annotations

VETS = ["Dr. Patel", "Dr. Nguyen", "Dr. Garcia", "Dr. Kim",
        "Dr. Johnson", "Dr. Smith", "Dr. Lee", "Dr. Brown"]
DURATIONS = ["2 days", "3 days", "5 days", "a week", "10 days", "two weeks"]
SEXES = ["neutered male", "spayed female", "intact male", "intact female"]

FILLERS = [
    "Vital signs stable at presentation.",
    "Patient bright and responsive on exam.",
    "Owner reports good appetite otherwise.",
    "No known drug allergies reported.",
    "Patient tolerated the examination well.",
    "Discussed home-care instructions with the owner.",
    "Recheck recommended if signs worsen.",
    "Medical record reviewed prior to visit.",
]

# Shared confusable pools ----------------------------------------------------
ORTHO_POOL = [  # Arthritis / Hip Dysplasia / Cruciate Ligament Tear
    "Patient shows lameness in the affected limb.",
    "Limping noted on gait examination.",
    "Reluctant to bear full weight on the leg.",
    "Difficulty rising from a lying position.",
    "Stiff gait observed after rest.",
    "Joint pain elicited on manipulation.",
    "Reduced range of motion in the joint.",
    "Orthopedic examination performed, radiographs recommended.",
    "Started on an NSAID for pain management.",
    "Prescribed carprofen for joint pain.",
    "Discussed joint supplements and weight management.",
    "Referred for physical rehabilitation evaluation.",
    "Cold laser therapy discussed as an adjunct.",
    "Exercise restriction advised for the next two weeks.",
]
DERM_POOL = [  # Skin Allergies / Ear Infection
    "Pruritus reported by the owner.",
    "Scratching noted at the affected area.",
    "Inflammation visible on examination.",
    "Erythema present at the lesion site.",
    "Cytology collected to check for secondary infection.",
    "Secondary bacterial infection suspected.",
]
GI_POOL = [  # Gastroenteritis / Diabetes (systemic overlap)
    "Patient appears lethargic today.",
    "Owner reports decreased appetite.",
    "Mild weight loss noted since the last visit.",
    "Bloodwork recommended to rule out systemic disease.",
    "Dehydration assessed at under five percent.",
]

# Per-category templates -----------------------------------------------------
# Slots: {pet} dog/cat, {breed}, {age}, {sex}, {vet}, {dur}, {sig}, {med}
NOTES = {
    "Gastroenteritis": {
        "present": [
            "Owner reports {sig} for the past {dur}.",
            "Patient presented with {sig} starting {dur} ago.",
            "History of {sig}; owner notes {sig} as well.",
            "Acute onset of {sig} reported this morning.",
        ],
        "exam": [
            "Abdomen soft with mild discomfort on palpation.",
            "Bowel sounds hyperactive in all quadrants.",
            "Mucous membranes pink, mild nausea suspected.",
            "Hydration adequate; no abdominal masses palpated.",
        ],
        "plan": [
            "Prescribed {med}; bland diet of boiled chicken and rice.",
            "Administered {med} in clinic; sent home with {med}.",
            "Withhold food for 12 hours, then reintroduce bland diet; {med} prescribed.",
            "Subcutaneous fluids given; {med} dispensed for nausea.",
        ],
        "sig": ["vomiting", "diarrhea", "repeated vomiting", "watery diarrhea",
                "nausea and drooling", "vomiting bile", "loose stools",
                "straining to defecate", "mucus in the stool"],
        "meds": ["maropitant", "metronidazole", "ondansetron", "probiotics",
                 "famotidine", "metoclopramide"],
        "confuse": ("GI_POOL", 0.40),
    },
    "Skin Allergies": {
        "present": [
            "Owner reports {sig} for the past {dur}.",
            "Patient presented for {sig}; signs recur every spring.",
            "Chronic history of {sig}, worse over the last {dur}.",
            "Intense {sig} keeping the {pet} up at night per owner.",
        ],
        "exam": [
            "Generalized erythema with excoriations on the ventrum.",
            "Interdigital redness and licking sores on the paws.",
            "Hot spots noted along the flank; coat dull.",
            "Skin scraping negative for mites; allergy suspected.",
        ],
        "plan": [
            "Started {med} for allergic pruritus.",
            "Prescribed {med}; oatmeal shampoo recommended twice weekly.",
            "Allergy workup discussed; {med} dispensed for itch control.",
            "Cytopoint injection administered; {med} sent home.",
        ],
        "sig": ["itchy skin", "constant scratching", "chewing at the paws",
                "red inflamed skin", "recurrent hot spots", "licking the belly raw",
                "seasonal itching", "hives along the back"],
        "meds": ["oclacitinib", "lokivetmab", "prednisone taper", "antihistamines",
                 "medicated shampoo", "omega-3 supplements"],
        "confuse": ("DERM_POOL", 0.55),
    },
    "Ear Infection": {
        "present": [
            "Owner reports {sig} for the past {dur}.",
            "Patient presented with {sig}; head tilt observed.",
            "Recurrent {sig}; third episode this year.",
            "Acute {sig} noticed after swimming last weekend.",
        ],
        "exam": [
            "Otoscopic exam reveals erythematous canals with discharge.",
            "Pinnae inflamed; odor present on examination.",
            "Tympanic membrane intact; moderate debris in the canal.",
            "Pain response on palpation of the ear base.",
        ],
        "plan": [
            "Ear cleaning performed; {med} prescribed.",
            "Dispensed {med} with instructions for twice-daily application.",
            "Recheck in {dur}; {med} continued until recheck.",
            "Culture submitted; started empirical {med}.",
        ],
        "sig": ["head shaking", "scratching at the ears", "foul odor from the ears",
                "brown waxy discharge", "tilting the head to one side",
                "crying when the ears are touched", "swollen ear flap"],
        "meds": ["otic enrofloxacin", "otic mometamax", "ear cleaner",
                 "otomax ointment", "tresaderm drops"],
        "confuse": ("DERM_POOL", 0.55),
    },
    "Urinary Tract Infection": {
        "present": [
            "Owner reports {sig} for the past {dur}.",
            "Patient presented with {sig} starting yesterday.",
            "History of {sig}; owner noticed accidents in the house.",
            "Recurrent {sig} per history.",
        ],
        "exam": [
            "Bladder small and painful on palpation.",
            "Urinalysis shows bacteriuria and struvite crystals.",
            "Urine dipstick positive for blood and leukocytes.",
            "External genitalia unremarkable; bladder wall thickened.",
        ],
        "plan": [
            "Urine culture submitted; started {med}.",
            "Prescribed {med} for 14 days; recheck urinalysis planned.",
            "Increased water intake encouraged; {med} dispensed.",
            "Radiographs to rule out bladder stones; {med} started.",
        ],
        "sig": ["straining to urinate", "blood in the urine",
                "frequent attempts to urinate", "urinating in small amounts",
                "cloudy foul-smelling urine", "licking the urinary opening",
                "crying while urinating"],
        "meds": ["amoxicillin-clavulanate", "cephalexin", "enrofloxacin",
                 "urinary diet", "cranberry supplements"],
        "confuse": (None, 0.0),
    },
    "Dental Disease": {
        "present": [
            "Owner reports {sig} for the past {dur}.",
            "Patient presented for {sig} noted during annual exam.",
            "Routine wellness visit revealed {sig}.",
            "Owner noticed {sig} while playing with the {pet}.",
        ],
        "exam": [
            "Grade 3 dental disease with heavy tartar accumulation.",
            "Gingivitis with bleeding on probing; halitosis present.",
            "Fractured upper premolar with pulp exposure.",
            "Multiple loose incisors; periodontal pockets measured.",
        ],
        "plan": [
            "Dental cleaning scheduled under anesthesia; {med} prescribed.",
            "Recommended {med} and full-mouth radiographs.",
            "Tooth extraction performed; {med} sent home for pain.",
            "Dental prophylaxis completed; {med} dispensed.",
        ],
        "sig": ["bad breath", "dropping food while eating",
                "pawing at the mouth", "bleeding gums", "yellow tartar on teeth",
                "reluctance to chew hard treats", "broken tooth"],
        "meds": ["dental prophylaxis", "clindamycin", "carprofen",
                 "chlorhexidine rinse", "dental diet"],
        "confuse": (None, 0.0),
    },
    "Kennel Cough": {
        "present": [
            "Owner reports {sig} for the past {dur}.",
            "Patient presented with {sig} after boarding last week.",
            "Acute onset {sig} reported this morning.",
            "Multiple dogs in the household showing {sig}.",
        ],
        "exam": [
            "Harsh dry cough easily induced on tracheal palpation.",
            "Lungs clear; honking cough characteristic of kennel cough.",
            "Mild serous nasal discharge; no fever detected.",
            "Tracheal sensitivity marked; otherwise bright.",
        ],
        "plan": [
            "Prescribed {med}; strict rest and isolation advised.",
            "Started {med} for cough suppression.",
            "Symptomatic care with {med}; recheck if cough persists past {dur}.",
            "Nebulization discussed; {med} dispensed.",
        ],
        "sig": ["harsh dry cough", "honking cough", "gagging after coughing",
                "coughing fits at night", "runny nose with cough",
                "sneezing and coughing", "retching like something stuck in throat"],
        "meds": ["doxycycline", "hydrocodone cough tablets", "honey and rest",
                 "nebulization", "bordetella booster"],
        "confuse": (None, 0.0),
    },
    "Conjunctivitis": {
        "present": [
            "Owner reports {sig} for the past {dur}.",
            "Patient presented with {sig} in both eyes.",
            "Acute {sig} noticed this morning.",
            "Recurrent {sig} per owner history.",
        ],
        "exam": [
            "Conjunctival hyperemia with mucopurulent discharge.",
            "Fluorescein stain negative; no corneal ulceration.",
            "Third eyelid elevated; mild chemosis present.",
            "Schirmer tear test within normal limits.",
        ],
        "plan": [
            "Prescribed {med} for both eyes twice daily.",
            "Dispensed {med}; warm compresses recommended.",
            "Recheck in {dur}; continue {med} until recheck.",
            "E-collar fitted to prevent rubbing; {med} started.",
        ],
        "sig": ["red itchy eyes", "green discharge from the eyes",
                "squinting in bright light", "swollen eyelids",
                "pawing at the eyes", "watery tearing", "crusty eyes in the morning"],
        "meds": ["ofloxacin eye drops", "erythromycin eye ointment",
                 "neomycin-polymyxin drops", "artificial tears"],
        "confuse": (None, 0.0),
    },
    "Laceration": {
        "present": [
            "Owner reports {sig} after the {pet} ran through brush {dur} ago.",
            "Patient presented with {sig} sustained during play.",
            "Acute {sig} noticed after a fight with another animal.",
            "Traumatic {sig} reported this evening.",
        ],
        "exam": [
            "Full-thickness laceration over the lateral thigh, edges clean.",
            "Wound measures 4 cm; moderate hemorrhage controlled with pressure.",
            "Puncture wound with surrounding swelling; no fracture suspected.",
            "Laceration through subcutaneous tissue; muscle intact.",
        ],
        "plan": [
            "Wound clipped, lavaged, and closed with {med}.",
            "Placed {med}; bandage applied with recheck in {dur}.",
            "Surgical repair under sedation; {med} prescribed.",
            "Tetanus risk assessed; {med} dispensed for infection prevention.",
        ],
        "sig": ["deep cut on the leg", "bleeding paw pad", "torn ear flap",
                "gash on the side", "bite wound on the neck",
                "cut paw that will not stop bleeding", "skin flap hanging loose"],
        "meds": ["sutures", "staples", "cephalexin", "carprofen",
                 "bandage changes", "tissue adhesive"],
        "confuse": (None, 0.0),
    },
    "Arthritis": {
        "present": [
            "Owner reports {sig} for the past {dur}.",
            "Patient presented for {sig}, worse in cold weather.",
            "Chronic {sig} gradually worsening over months.",
            "Senior wellness visit; owner notes {sig}.",
        ],
        "exam": [
            "Bilateral hip stiffness; crepitus on joint manipulation.",
            "Reduced hind-limb muscle mass consistent with chronic arthritis.",
            "Radiographs show osteophyte formation at multiple joints.",
            "Slow to rise; short-strided gait in the hind limbs.",
        ],
        "plan": [
            "Started {med} for chronic arthritis management.",
            "Prescribed {med}; weight-loss plan initiated.",
            "Adequan injections discussed; {med} dispensed.",
            "Multimodal pain plan with {med} and rehabilitation.",
        ],
        "sig": ["stiffness after rest", "slowing down on walks",
                "trouble climbing stairs", "stiff joints in the morning",
                "lagging behind on walks", "creaky joints"],
        "meds": ["galliprant", "carprofen", "adequan injections",
                 "gabapentin", "joint supplements", "librela injection"],
        "confuse": ("ORTHO_POOL", 0.85),
    },
    "Cruciate Ligament Tear": {
        "present": [
            "Owner reports {sig} after chasing a ball {dur} ago.",
            "Patient presented with acute {sig}; non-weight-bearing.",
            "Sudden {sig} noticed after jumping off the couch.",
            "History of intermittent {sig} now acutely worse.",
        ],
        "exam": [
            "Positive cranial drawer sign; stifle effusion present.",
            "Tibial thrust evident; cranial cruciate rupture diagnosed.",
            "Stifle radiographs show joint effusion and early arthritis.",
            "Marked quadriceps atrophy on the affected limb.",
        ],
        "plan": [
            "TPLO surgery scheduled; {med} prescribed pre-operatively.",
            "Referred to surgery for {med}; strict crate rest meanwhile.",
            "Post-op rehabilitation plan outlined; {med} dispensed.",
            "Stifle brace discussed as a conservative option; {med} started.",
        ],
        "sig": ["sudden hind-leg lameness", "toe-touching on one back leg",
                "knee giving out", "swollen knee joint",
                "yelping when the back leg is touched", "leg carried off the ground"],
        "meds": ["TPLO surgery", "trazodone for rest", "carprofen",
                 "gabapentin", "cold therapy", "lateral suture surgery"],
        "confuse": ("ORTHO_POOL", 0.85),
    },
    "Hip Dysplasia": {
        "present": [
            "Owner reports {sig} for the past {dur}.",
            "Patient presented for {sig} since puppyhood.",
            "Young {breed} with {sig} on exercise.",
            "Bunny-hopping gait; owner reports {sig}.",
        ],
        "exam": [
            "Positive Ortolani sign; hip laxity confirmed.",
            "Radiographs show shallow acetabula and femoral head remodeling.",
            "Pain on hip extension; decreased hind-limb muscling.",
            "Bunny-hopping gait observed at a trot.",
        ],
        "plan": [
            "Started {med}; juvenile pubic symphysiodesis discussed.",
            "Prescribed {med} with a controlled exercise program.",
            "Total hip replacement consultation scheduled; {med} meanwhile.",
            "Femoral head ostectomy discussed as an option; {med} dispensed.",
        ],
        "sig": ["bunny-hopping when running", "loose hips",
                "clicking sound from the hips", "swaying walk in the back end",
                "difficulty jumping into the car", "hips giving way on stairs"],
        "meds": ["carprofen", "dasuquin", "physical therapy",
                 "total hip replacement", "FHO surgery", "galliprant"],
        "confuse": ("ORTHO_POOL", 0.85),
    },
    "Diabetes": {
        "present": [
            "Owner reports {sig} for the past {dur}.",
            "Patient presented with {sig}; drinking excessively.",
            "Senior wellness bloodwork flagged {sig}.",
            "Weight loss despite good appetite; {sig} reported.",
        ],
        "exam": [
            "Blood glucose markedly elevated; glucosuria present.",
            "Cataracts noted on ophthalmic exam; diabetic suspected.",
            "Body condition score low; dehydration mild.",
            "Fructosamine elevated consistent with diabetes mellitus.",
        ],
        "plan": [
            "Started {med}; glucose curve scheduled next week.",
            "Prescribed {med} with a high-fiber diabetic diet.",
            "Insulin dosing demonstration completed; {med} dispensed.",
            "Home glucose monitoring discussed; {med} initiated.",
        ],
        "sig": ["excessive thirst", "frequent urination",
                "drinking bowls of water at once", "sweet-smelling breath",
                "sudden blindness from cataracts", "eating more but losing weight"],
        "meds": ["vetsulin", "prozinc insulin", "diabetic diet",
                 "glucose curve", "alphaTRAK monitoring"],
        "confuse": ("GI_POOL", 0.40),
    },
}

POOLS = {"ORTHO_POOL": ORTHO_POOL, "DERM_POOL": DERM_POOL, "GI_POOL": GI_POOL}

# Generic exam/plan sentences shared across ALL categories. Real notes are
# full of boilerplate; the boilerplate dilutes category-specific signal.
GENERAL_EXAM = [
    "Physical examination unremarkable aside from the presenting complaint.",
    "Vital parameters within normal limits.",
    "No abnormalities detected on systemic examination.",
    "Patient alert with normal hydration status.",
    "Cardiopulmonary auscultation within normal limits.",
    "Abdominal palpation unremarkable.",
]
GENERAL_PLAN = [
    "Symptomatic treatment initiated as described above.",
    "Owner advised to monitor closely and return if signs persist.",
    "Recheck examination scheduled as needed.",
    "Treatment plan discussed at length with the owner.",
    "Patient discharged in stable condition with home-care instructions.",
    "Follow-up recommended if there is no improvement.",
]

# Shared orthopedic sentence banks. The arthritis / hip-dysplasia /
# cruciate-tear trio presents almost identically in notes (lameness, joint
# pain, NSAIDs, rehab); only a minority of sentences carry the
# distinguishing details (drawer sign vs Ortolani vs chronic stiffness).
ORTHO_PRESENT = [
    "Owner reports hind-limb lameness for the past {dur}.",
    "Patient presented with difficulty rising and general stiffness.",
    "Intermittent limping noted, worse after exercise.",
    "Owner reports the {pet} is slowing down and reluctant to play.",
    "Lameness first noticed {dur} ago, now persistent.",
    "Patient holds up one hind leg when standing.",
]
ORTHO_EXAM = [
    "Gait examination reveals hind-limb lameness.",
    "Joint effusion with pain on manipulation of the limb.",
    "Radiographs show degenerative changes in the joint.",
    "Decreased muscle mass over the affected hindquarter.",
    "Stifle and hip palpation elicit a pain response.",
    "Thickened joint capsule appreciated on palpation.",
]
ORTHO_PLAN = [
    "Started {med} for musculoskeletal pain management.",
    "Prescribed {med}; strict exercise restriction advised.",
    "Weight-management plan initiated alongside {med}.",
    "Referred for rehabilitation assessment; {med} dispensed.",
    "Surgical consultation discussed; {med} started meanwhile.",
    "Cold therapy and {med} recommended for flare-ups.",
]
ORTHO_MEDS = ["carprofen", "galliprant", "gabapentin", "meloxicam",
              "joint supplements", "trazodone for rest"]

__all__ = ["NOTES", "POOLS", "VETS", "DURATIONS", "SEXES", "FILLERS",
           "GENERAL_EXAM", "GENERAL_PLAN",
           "ORTHO_PRESENT", "ORTHO_EXAM", "ORTHO_PLAN", "ORTHO_MEDS"]
