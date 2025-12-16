from typing import List, Dict, Any

CURATED_HEALTH_MYTHS = [
    {
        "claim": "Hot water cures malaria",
        "verdict": "FALSE",
        "confidence": 95,
        "explanation": "Malaria is caused by Plasmodium parasites transmitted through mosquito bites. It requires antimalarial medication like Artemisinin-based Combination Therapies (ACTs). Hot water has no effect on the parasites in your bloodstream.",
        "sources": [
            "WHO Malaria Treatment Guidelines 2023",
            "Nigerian Federal Ministry of Health - Malaria Treatment Protocol",
            "Nigeria Centre for Disease Control (NCDC)"
        ],
        "category": "malaria",
        "language": "en"
    },
    {
        "claim": "Sugar causes diabetes",
        "verdict": "PARTIALLY TRUE",
        "confidence": 70,
        "explanation": "Eating too much sugar does not directly cause diabetes, but it can lead to weight gain, which is a risk factor for Type 2 diabetes. The actual cause is insulin resistance, which develops over time due to genetics, lifestyle, and obesity.",
        "sources": [
            "WHO - Diabetes Fact Sheet",
            "American Diabetes Association Guidelines",
            "Nigerian Endocrine Society"
        ],
        "category": "diabetes",
        "language": "en"
    },
    {
        "claim": "Malaria and COVID-19 are the same disease",
        "verdict": "FALSE",
        "confidence": 99,
        "explanation": "Malaria is caused by parasites spread by mosquitoes, while COVID-19 is caused by the SARS-CoV-2 virus spread through respiratory droplets. They have different symptoms, treatments, and prevention methods. Both can cause fever, but malaria also causes chills and sweating, while COVID affects breathing.",
        "sources": [
            "NCDC Nigeria - COVID-19 vs Malaria Comparison",
            "WHO - Disease Comparison Guidelines"
        ],
        "category": "malaria,covid",
        "language": "en"
    },
    {
        "claim": "Antibiotics cure viral infections like flu",
        "verdict": "FALSE",
        "confidence": 98,
        "explanation": "Antibiotics only work against bacterial infections. Viral infections like flu, cold, and COVID-19 are not affected by antibiotics. Taking antibiotics for viral infections can lead to antibiotic resistance, making them less effective when you really need them.",
        "sources": [
            "WHO - Antimicrobial Resistance Guidelines",
            "Nigerian NCDC - Antibiotic Stewardship",
            "Nigerian Medical Association"
        ],
        "category": "antibiotics",
        "language": "en"
    },
    {
        "claim": "Sleeping under a fan causes cold and pneumonia",
        "verdict": "FALSE",
        "confidence": 85,
        "explanation": "Colds are caused by viruses, not cold air. While sleeping under a fan might make you feel cold or cause muscle stiffness, it does not directly cause viral infections or pneumonia. You catch a cold when you're exposed to cold viruses from other people.",
        "sources": [
            "Mayo Clinic - Common Cold Myths",
            "Nigerian Medical Journal on Common Misconceptions"
        ],
        "category": "respiratory",
        "language": "en"
    },
    {
        "claim": "Saltwater cures Ebola",
        "verdict": "FALSE",
        "confidence": 99,
        "explanation": "This dangerous myth spread during the 2014 Ebola outbreak in West Africa. Drinking or bathing in saltwater does not cure Ebola and can cause serious health problems including dehydration and kidney damage. Ebola requires medical treatment in isolation facilities with supportive care.",
        "sources": [
            "WHO - Ebola Treatment Guidelines",
            "NCDC Nigeria - Ebola Response Documentation",
            "Nigerian Federal Ministry of Health Emergency Response"
        ],
        "category": "ebola",
        "language": "en"
    },
    {
        "claim": "Hypertension can be cured permanently",
        "verdict": "FALSE",
        "confidence": 90,
        "explanation": "Hypertension (high blood pressure) is usually a chronic condition that requires lifelong management through medication, diet, and lifestyle changes. While blood pressure can be controlled and maintained at healthy levels, most cases cannot be 'cured' permanently. Do not stop taking your medication without consulting a doctor.",
        "sources": [
            "WHO - Hypertension Management Guidelines",
            "Nigerian Heart Foundation",
            "Nigerian Cardiac Society"
        ],
        "category": "hypertension",
        "language": "en"
    },
    {
        "claim": "Herbal mixtures can cure HIV/AIDS",
        "verdict": "FALSE",
        "confidence": 99,
        "explanation": "There is no cure for HIV/AIDS. While antiretroviral therapy (ART) can effectively manage HIV and allow people to live long healthy lives, herbal mixtures have not been scientifically proven to cure HIV. Relying on unproven treatments instead of ART can be deadly. Always consult with healthcare providers.",
        "sources": [
            "WHO - HIV Treatment Guidelines",
            "NACA Nigeria (National Agency for Control of AIDS)",
            "Nigerian Institute of Medical Research"
        ],
        "category": "hiv",
        "language": "en"
    },
    {
        "claim": "You should starve a fever",
        "verdict": "FALSE",
        "confidence": 85,
        "explanation": "The saying 'starve a fever, feed a cold' is a myth. When you have a fever, your body needs energy to fight infection. You should eat nutritious foods and stay well-hydrated with water, soups, and electrolyte drinks. Starving yourself will weaken your immune system.",
        "sources": [
            "Mayo Clinic - Fever Treatment",
            "WHO - Nutrition During Illness"
        ],
        "category": "fever",
        "language": "en"
    },
    {
        "claim": "Eating late at night directly causes weight gain",
        "verdict": "PARTIALLY TRUE",
        "confidence": 60,
        "explanation": "Weight gain is about total calories consumed versus calories burned throughout the day, not specifically about when you eat. However, people who eat late at night tend to snack on high-calorie foods and may exceed their daily calorie needs. The timing itself is not the main cause - it's about total intake.",
        "sources": [
            "British Journal of Nutrition - Meal Timing Research",
            "Nigerian Nutrition Society"
        ],
        "category": "nutrition",
        "language": "en"
    },
    {
        "claim": "Bitter kola cures COVID-19",
        "verdict": "FALSE",
        "confidence": 95,
        "explanation": "While bitter kola (Garcinia kola) has some health benefits and is used in traditional medicine, there is no scientific evidence that it cures or prevents COVID-19. The best protection is vaccination, mask-wearing, and following public health guidelines.",
        "sources": [
            "NCDC Nigeria - COVID-19 Mythbusting",
            "WHO - Traditional Medicine and COVID-19"
        ],
        "category": "covid",
        "language": "en"
    },
    {
        "claim": "Drinking hot drinks prevents COVID-19",
        "verdict": "FALSE",
        "confidence": 92,
        "explanation": "Drinking hot beverages does not prevent COVID-19 infection. The virus enters through the respiratory system, not the digestive system. The best prevention methods are vaccination, wearing masks, social distancing, and hand hygiene.",
        "sources": [
            "WHO - COVID-19 Myth Busters",
            "NCDC Nigeria Public Health Advisory"
        ],
        "category": "covid",
        "language": "en"
    },
    {
        "claim": "Typhoid can be cured by eating unripe pawpaw",
        "verdict": "FALSE",
        "confidence": 88,
        "explanation": "Typhoid fever is a serious bacterial infection that requires antibiotic treatment prescribed by a doctor. While some people believe unripe pawpaw helps, there is no scientific evidence it cures typhoid. Untreated typhoid can be life-threatening. Always seek medical care.",
        "sources": [
            "WHO - Typhoid Treatment Guidelines",
            "Nigerian Medical Association",
            "Federal Ministry of Health Nigeria"
        ],
        "category": "typhoid",
        "language": "en"
    },
    {
        "claim": "Bathing a baby with cold water makes them strong",
        "verdict": "FALSE",
        "confidence": 90,
        "explanation": "Bathing babies with cold water does not make them stronger. In fact, cold water can be harmful to babies as they cannot regulate their body temperature well. Babies should be bathed with warm (not hot) water for comfort and safety.",
        "sources": [
            "WHO - Newborn Care Guidelines",
            "Nigerian Paediatric Association",
            "UNICEF Nigeria - Child Care"
        ],
        "category": "child_health",
        "language": "en"
    },
    {
        "claim": "Putting thread on a baby's head stops hiccups",
        "verdict": "FALSE",
        "confidence": 80,
        "explanation": "This is a cultural belief without scientific basis. Baby hiccups are normal and usually harmless. They often stop on their own. Placing thread or objects on a baby's forehead does not affect the diaphragm muscle that causes hiccups. Hiccups usually resolve naturally within a few minutes.",
        "sources": [
            "Nigerian Paediatric Association",
            "American Academy of Pediatrics - Newborn Care"
        ],
        "category": "child_health",
        "language": "en"
    }
]

def get_all_myths() -> List[Dict[str, Any]]:
    """Get all curated health myths."""
    return CURATED_HEALTH_MYTHS

def get_myths_by_category(category: str) -> List[Dict[str, Any]]:
    """Get myths filtered by category."""
    return [myth for myth in CURATED_HEALTH_MYTHS if category in myth['category']]

