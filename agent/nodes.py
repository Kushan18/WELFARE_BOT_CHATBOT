from db_utils import get_mongo_client
import os
import re
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

import motor.motor_asyncio
from groq import Groq
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY environment variable not set")
MONGODB_URI = os.getenv("MONGODB_URI")
if not MONGODB_URI:
    raise RuntimeError("MONGODB_URI environment variable not set")

# Initialize Groq client (will be set by main.py)
groq_client = None

# Initialize MongoDB clients (will be set by main.py)
sync_users_collection = None
sync_schemes_collection = None
sync_reminders_collection = None
conversations_collection = None

# Set up MongoDB connection if running standalone
if not groq_client:
    import motor.motor_asyncio
    sync_mongo_client = get_mongo_client(MONGODB_URI)
    async_mongo_client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URI)
    sync_users_collection = sync_mongo_client["welfarebot"]["users"]
    sync_schemes_collection = sync_mongo_client["welfarebot"]["schemes"]
    sync_reminders_collection = sync_mongo_client["welfarebot"]["reminders"]
    conversations_collection = async_mongo_client["welfarebot"]["conversations"]
    groq_client = Groq(api_key=GROQ_API_KEY)

# Logging
logger = logging.getLogger(__name__)

# ---------- Language Translations & Helpers ----------
ONBOARDING_TRANSLATIONS = {
    "en": {
        "state_q": "Which state are you from?",
        "occupation_q": "What is your occupation? (Student, Farmer, Daily Wage Worker, Self Employed, Government Employee, Other)",
        "caste_category_q": "What is your caste category? (SC, ST, OBC, General, EWS)",
        "gender_q": "What is your gender? (Male, Female, Other)",
        "age_q": "How old are you?",
        "income_bracket_q": "What is your annual family income?",
        "land_size_q": "How much agricultural land do you own (in acres)? (Enter 0 if none)",
        "email_q": "What is your email address? (Optional - type 'skip' to skip)",
        "confirm_header": "Please confirm your details:\n\n",
        "confirm_name": "👤 **Name**",
        "confirm_lang": "🗣️ **Language**",
        "confirm_lang_name": "English",
        "confirm_state": "📍 **State**",
        "confirm_occup": "💼 **Occupation**",
        "confirm_caste": "🏷️ **Caste Category**",
        "confirm_gender": "🚻 **Gender**",
        "confirm_age": "🎂 **Age**",
        "confirm_income": "💰 **Annual Income**",
        "confirm_land": "🌾 **Land Size**",
        "confirm_email": "📧 **Email**",
        "confirm_not_provided": "Not provided",
        "confirm_acres": "acres",
        "confirm_question": "Is this information correct? (Yes/No)",
        "yes": "Yes",
        "no": "No",
        "correct_prompt": "Please confirm if your details are correct. Answer 'Yes' or 'No'.",
        "edit_which": "Which detail would you like to edit?",
        "edit_prompt": "Please select one of the fields to edit: Name, State, Occupation, Caste Category, Gender, Age, Income Bracket, Land Size, or Email.",
        "edit_new_val": "Please enter your new ",
        "invalid_age": "Please enter a valid age (between 1 and 120).",
        "invalid_land": "Please enter a valid land size in acres (e.g. 0 or 2.5).",
        "invalid_email": "Please enter a valid email address or type 'skip' to skip.",
        "chat_choice_prompt": "Let's collect your details in chat. Which state do you live in?",
        "form_choice_prompt": "I've opened the profile form. Please fill out your details so I can match you with eligible schemes.",
        "form_choice_fallback": "Please fill out the profile form to continue, or type 'Chat Instead' to answer questions here.",
        "no_match": "No exact matches found right now. Check back later for new schemes!",
        "found_matches": "I found {count} schemes that match your profile! Select a scheme to learn more:",
        "error_fetching": "I'm having trouble fetching schemes right now. Please try again later.",
        "skip_email_chip": "Skip Email",
        "chat_instead_chip": "💬 Chat Instead",
        "fill_form_chip": "📝 Fill Form",
        "states": ["Andhra Pradesh", "Telangana", "Delhi", "Maharashtra", "Tamil Nadu"],
        "occupations": ["Student", "Farmer", "Daily Wage Worker", "Self Employed", "Government Employee", "Other"],
        "castes": ["General", "OBC", "SC", "ST", "EWS"],
        "genders": ["Male", "Female", "Other"],
        "incomes": ["Below 1 Lakh", "1-2.5 Lakh", "2.5-5 Lakh", "5-10 Lakh", "Above 10 Lakh"],
        "lands": ["0", "1-2 acres", "3-5 acres", "5+ acres"],
        "name_step_reply": "Hi {name}! 😊\n\nWhich language do you prefer to continue?",
        "form_chat_intro": "Great! I'm here to help you discover government welfare schemes you're eligible for.\n\nI can find schemes based on your profile, explain benefits, and help you understand application processes.\n\nWould you like to:\n- Fill a form with your details (recommended)\n- Chat with me directly step-by-step right here\n\nPlease choose: 'Fill Form' or 'Chat Instead'",

        "phone_prompt": "What is your phone number? (10 digits)",
        "phone_invalid": "Please enter a valid 10-digit phone number.",
        "welcome": "Welcome back, {name}! We're glad to see you again. Please select your preferred language to continue:",
        "pin_setup": "To keep your account secure, please set up a 4-digit PIN.",
        "pin_enter": "Welcome! Please enter your 4-digit PIN to securely log in.",
        "pin_confirm": "Please confirm your 4-digit PIN.",
        "pin_saved": "✅ Your PIN has been securely saved.",
        "welcome_bot": "It's wonderful to meet you, {name}! Welcome to WelfareBot.\n\nI'm here to guide you through finding government welfare schemes you're eligible for — based on details like your state, occupation, income, and a few other things. Once I know a bit about you, I'll show you every scheme that matches, and I can also answer questions about how to apply.",
        "pin_consent": "Before we continue, I'll ask you to set up a 4-digit PIN — this keeps your account and details secure. Ready to proceed?",
        "welcome_back": "Good to see you again, {name}! Welcome back to WelfareBot. I've got your details saved, and there may be new schemes available since you last checked.",
        "proceed_chip": "✅ Proceed",
        "not_now_chip": "Not now",
        "forgot_pin": "Forgot PIN?"
    },
    "hi": {
        "state_q": "आप किस राज्य से हैं?",
        "occupation_q": "आपका व्यवसाय क्या है? (छात्र, किसान, दैनिक वेतन भोगी, स्व-नियोजित, सरकारी कर्मचारी, अन्य)",
        "caste_category_q": "आपकी जाति श्रेणी क्या है? (SC, ST, OBC, सामान्य, EWS)",
        "gender_q": "आपका लिंग क्या है? (पुरुष, महिला, अन्य)",
        "age_q": "आपकी उम्र क्या है?",
        "income_bracket_q": "आपकी वार्षिक पारिवारिक आय क्या है?",
        "land_size_q": "आपके पास कितनी कृषि भूमि है (एकड़ में)? (यदि कोई नहीं है तो 0 दर्ज करें)",
        "email_q": "आपका ईमेल पता क्या है? (वैकल्पिक - छोड़ने के लिए 'skip' टाइप करें)",
        "confirm_header": "कृपया अपने विवरण की पुष्टि करें:\n\n",
        "confirm_name": "👤 **नाम**",
        "confirm_lang": "🗣️ **भाषा**",
        "confirm_lang_name": "Hindi (हिंदी)",
        "confirm_state": "📍 **राज्य**",
        "confirm_occup": "💼 **व्यवसाय**",
        "confirm_caste": "🏷️ **जाति श्रेणी**",
        "confirm_gender": "🚻 **लिंग**",
        "confirm_age": "🎂 **उम्र**",
        "confirm_income": "💰 **वार्षिक आय**",
        "confirm_land": "🌾 **भूमि का आकार**",
        "confirm_email": "📧 **ईमेल**",
        "confirm_not_provided": "प्रदान नहीं किया गया",
        "confirm_acres": "एकड़",
        "confirm_question": "क्या यह जानकारी सही है? (हाँ/नहीं)",
        "yes": "हाँ",
        "no": "नहीं",
        "correct_prompt": "कृपया पुष्टि करें कि क्या आपका विवरण सही है। 'हाँ' या 'नहीं' में उत्तर दें।",
        "edit_which": "आप किस विवरण को संपादित करना चाहेंगे?",
        "edit_prompt": "कृपया संपादित करने के लिए किसी एक फ़ील्ड का चयन करें: नाम, राज्य, व्यवसाय, जाति श्रेणी, लिंग, उम्र, आय श्रेणी, भूमि का आकार, या ईमेल।",
        "edit_new_val": "कृपया अपना नया दर्ज करें: ",
        "invalid_age": "कृपया एक वैध उम्र दर्ज करें (1 और 120 के बीच)।",
        "invalid_land": "कृपया एकड़ में एक वैध भूमि का आकार दर्ज करें (जैसे 0 या 2.5)।",
        "invalid_email": "कृपया एक वैध ईमेल पता दर्ज करें या छोड़ने के लिए 'skip' टाइप करें।",
        "chat_choice_prompt": "आइए चैट में आपका विवरण एकत्र करें। आप किस राज्य में रहते हैं?",
        "form_choice_prompt": "मैंने प्रोफ़ाइल फ़ॉर्म खोल दिया है। कृपया अपना विवरण भरें ताकि मैं आपको योग्य योजनाओं से मिला सकूं।",
        "form_choice_fallback": "कृपया जारी रखने के लिए प्रोफ़ाइल फ़ॉर्म भरें, या यहाँ प्रश्नों के उत्तर देने के लिए 'चैट करें' टाइप करें।",
        "no_match": "अभी कोई सटीक योजना नहीं मिली। नई योजनाओं के लिए बाद में देखें!",
        "found_matches": "मुझे {count} योजनाएं मिली हैं जो आपकी प्रोफ़ाइल से मेल खाती हैं! अधिक जानने के लिए किसी योजना का चयन करें:",
        "error_fetching": "मुझे अभी योजनाएं लाने में परेशानी हो रही है। कृपया बाद में पुनः प्रयास करें।",
        "skip_email_chip": "ईमेल छोड़ें",
        "chat_instead_chip": "💬 चैट करें",
        "fill_form_chip": "📝 फ़ॉर्म भरें",
        "states": ["आंध्र प्रदेश", "तेलंगाना", "दिल्ली", "महाराष्ट्र", "तमिलनाडु"],
        "occupations": ["छात्र", "किसान", "दैनिक वेतन भोगी", "स्व-नियोजित", "सरकारी कर्मचारी", "अन्य"],
        "castes": ["सामान्य", "OBC", "SC", "ST", "EWS"],
        "genders": ["पुरुष", "महिला", "अन्य"],
        "incomes": ["1 लाख से कम", "1-2.5 लाख", "2.5-5 लाख", "5-10 लाख", "10 लाख से अधिक"],
        "lands": ["0", "1-2 एकड़", "3-5 एकड़", "5+ एकड़"],
        "name_step_reply": "नमस्ते {name}! 😊\n\nजारी रखने के लिए आप कौन सी भाषा पसंद करते हैं?",
        "form_chat_intro": "बहुत बढ़िया! मैं यहाँ सरकारी कल्याणकारी योजनाओं को खोजने में आपकी मदद करने के लिए हूँ जिनके लिए आप पात्र हैं।\n\nमैं आपकी प्रोफ़ाइल के आधार पर योजनाएं खोज सकता हूँ, लाभों को समझा सकता हूँ और आवेदन प्रक्रियाओं को समझने में मदद कर सकता हूँ।\n\nक्या आप पसंद करेंगे:\n- अपने विवरण के साथ एक फ़ॉर्म भरें (अनुशंसित)\n- सीधे यहीं मेरे साथ चैट करें\n\nकृपया चुनें: 'फ़ॉर्म भरें' या 'चैट करें'",

        "phone_prompt": "आपका फ़ोन नंबर क्या है? (10 अंक)",
        "phone_invalid": "कृपया एक वैध 10-अंकीय फ़ोन नंबर दर्ज करें।",
        "welcome": "वापसी पर स्वागत है, {name}! वेलफेयरबॉट हमेशा आपकी मदद के लिए यहाँ है। आप किस भाषा में जारी रखना चाहेंगे?",
        "pin_setup": "वेलफेयरबॉट के साथ आगे बढ़ने के लिए, आपको सुरक्षा कारणों से 4-अंकीय पिन सेट करना होगा।",
        "pin_enter": "वेलफेयरबॉट में सफलतापूर्वक प्रवेश करने के लिए, कृपया अपना पिन दर्ज करें।",
        "pin_confirm": "अपने पिन की पुष्टि करें",
        "pin_saved": "✅ आपका पिन सेव हो गया है! इसे किसी के साथ साझा न करें।",
        "welcome_bot": "आपसे मिलकर बहुत खुशी हुई, {name}! WelfareBot में आपका स्वागत है। मैं आपको उन सरकारी कल्याणकारी योजनाओं को खोजने में मदद करने के लिए यहाँ हूँ जिनके आप योग्य हैं - आपके राज्य, व्यवसाय, आय जैसी जानकारी के आधार पर। एक बार जब मैं आपके बारे में जान लूँगा, तो मैं आपको हर वो योजना दिखाऊँगा जो आपसे मेल खाती है, और आवेदन कैसे करें, इससे जुड़े सवालों के जवाब भी दूँगा। (Draft)",
        "pin_consent": "आगे बढ़ने से पहले, मैं आपसे 4-अंकीय पिन सेट करने के लिए कहूँगा - यह आपके अकाउंट और जानकारी को सुरक्षित रखता है। क्या आप तैयार हैं? (Draft)",
        "welcome_back": "आपको फिर से देखकर अच्छा लगा, {name}! WelfareBot में वापसी पर स्वागत है। मैंने आपकी जानकारी सुरक्षित रखी है, और हो सकता है पिछली बार जब आपने चेक किया था तब से कुछ नई योजनाएं उपलब्ध हों। (Draft)",
        "proceed_chip": "✅ आगे बढ़ें",
        "not_now_chip": "अभी नहीं",
        "forgot_pin": "पिन भूल गए?"
    },
    "te": {
        "state_q": "మీరు ఏ రాష్ట్రం నుండి వచ్చారు?",
        "occupation_q": "మీ వృత్తి ఏమిటి? (విద్యార్థి, రైతు, రోజువారీ కూలీ, స్వయం ఉపాధి, ప్రభుత్వ ఉద్యోగి, ఇతర)",
        "caste_category_q": "మీ కుల వర్గం ఏమిటి? (SC, ST, OBC, జనరల్, EWS)",
        "gender_q": "మీ లింగం ఏమిటి? (పురుషుడు, స్త్రీ, ఇతర)",
        "age_q": "మీ వయస్సు ఎంత?",
        "income_bracket_q": "మీ వార్షిక కుటుంబ ఆదాయం ఎంత?",
        "land_size_q": "మీకు ఎంత వ్యవసాయ భూమి ఉంది (ఎకరాలలో)? (లేకపోతే 0 నమోదు చేయండి)",
        "email_q": "మీ ఇమెయిల్ చిరునామా ఏమిటి? (ఆప్షనల్ - దాటవేయడానికి 'skip' అని టైప్ చేయండి)",
        "confirm_header": "దయచేసి మీ వివరాలను ధృవీకరించండి:\n\n",
        "confirm_name": "👤 **పేరు**",
        "confirm_lang": "🗣️ **భాష**",
        "confirm_lang_name": "Telugu (తెలుగు)",
        "confirm_state": "📍 **రాష్ట్రం**",
        "confirm_occup": "💼 **వృత్తి**",
        "confirm_caste": "🏷️ **కుల వర్గం**",
        "confirm_gender": "🚻 **లింగం**",
        "confirm_age": "🎂 **వయస్సు**",
        "confirm_income": "💰 **వార్షిక ఆదాయం**",
        "confirm_land": "🌾 **భూమి పరిమాణం**",
        "confirm_email": "📧 **ఇమెయిల్**",
        "confirm_not_provided": "అందించబడలేదు",
        "confirm_acres": "ఎకరాలు",
        "confirm_question": "ఈ సమాచారం సరైనదేనా? (అవును/కాదు)",
        "yes": "అవును",
        "no": "కాదు",
        "correct_prompt": "దయచేసి మీ వివరాలు సరైనవో కాదో ధృవీకరించండి. 'అవును' లేదా 'కాదు' అని సమాధానం ఇవ్వండి.",
        "edit_which": "మీరు ఏ వివరాలను సవరించాలనుకుంటున్నారు?",
        "edit_fields": ["పేరు", "రాష్ట్రం", "వృత్తి", "కుల వర్గం", "లింగం", "వయస్సు", "ఆదాయ పరిమితి", "భూమి పరిమాణం", "ఇమెయిల్"],
        "edit_prompt": "సవరించడానికి ఈ క్రింది వాటిలో ఒకదాన్ని ఎంచుకోండి: పేరు, రాష్ట్రం, వృత్తి, కుల వర్గం, లింగం, వయస్సు, ఆదాయ పరిమితి, భూమి పరిమాణం లేదా ఇమెయిల్.",
        "edit_new_val": "దయచేసి మీ కొత్త విలువను నమోదు చేయండి: ",
        "invalid_age": "దయచేసి సరైన వయస్సును నమోదు చేయండి (1 నుండి 120 మధ్య).",
        "invalid_land": "దయచేసి ఎకరాలలో సరైన భూమి పరిమాణాన్ని నమోదు చేయండి (ఉదా. 0 లేదా 2.5).",
        "invalid_email": "దయచేసి సరైన ఇమెయిల్ చిరునామాను నమోదు చేయండి లేదా దాటవేయడానికి 'skip' అని టైప్ చేయండి.",
        "chat_choice_prompt": "చాట్‌లో మీ వివరాలను సేకరిద్దాం. మీరు ఏ రాష్ట్రంలో నివసిస్తున్నారు?",
        "form_choice_prompt": "నేను ప్రొఫైల్ ఫారమ్‌ను తెరిచాను. దయచేసి మీ వివరాలను పూరించండి, తద్వారా నేను మీకు తగిన పథకాలను కనుగొనగలను.",
        "form_choice_fallback": "కొనసాగించడానికి దయచేసి ప్రొఫైల్ ఫారమ్‌ను పూరించండి లేదా ఇక్కడ ప్రశ్నలకు సమాధానం ఇవ్వడానికి 'చాట్ చేయి' అని టైప్ చేయండి.",
        "no_match": "ప్రస్తుతం ఖచ్చితమైన పథకాలు ఏవీ కనుగొనబడలేదు. కొత్త పథకాల కోసం తర్వాత తనిఖీ చేయండి!",
        "found_matches": "మీ ప్రొఫైల్‌కు సరిపోయే {count} పథకాలను నేను కనుగన్నాను! మరింత తెలుసుకోవడానికి పథకాన్ని ఎంచుకోండి:",
        "error_fetching": "ప్రస్తుతం పథకాలను పొందడంలో నాకు ఇబ్బందిగా ఉంది. దయచేసి తర్వాత మళ్లీ ప్రయత్నించండి.",
        "skip_email_chip": "ఇమెయిల్ దాటవేయి",
        "chat_instead_chip": "💬 చాట్ చేయి",
        "fill_form_chip": "📝 ఫారమ్ పూరించు",
        "states": ["ఆంధ్రప్రదేశ్", "తెలంగాణ", "ఢిల్లీ", "మహారాష్ట్ర", "తమిళనాడు"],
        "occupations": ["విద్యార్థి", "రైతు", "రోజువారీ కూలీ", "స్వయం ఉపాధి", "ప్రభుత్వ ఉద్యోగి", "ఇతర"],
        "castes": ["జనరల్", "OBC", "SC", "ST", "EWS"],
        "genders": ["పురుషుడు", "స్త్రీ", "ఇతర"],
        "incomes": ["1 లక్ష కంటే తక్కువ", "1-2.5 లక్షలు", "2.5-5 లక్షలు", "5-10 లక్షలు", "10 లక్షల కంటే ఎక్కువ"],
        "lands": ["0 ఎకరాలు", "1-2 ఎకరాలు", "3-5 ఎకరాలు", "5+ ఎకరాలు"],
        "name_step_reply": "హాయ్ {name}! 😊\n\nకొనసాగించడానికి మీరు ఏ భాషను ఇష్టపడతారు?",
        "form_chat_intro": "అద్భుతం! మీరు అర్హులైన ప్రభుత్వ సంక్షేమ పథకాలను కనుగొనడంలో సహాయపడటానికి నేను ఇక్కడ ఉన్నాను.\n\nనేను మీ ప్రొఫైల్ ఆధారంగా పథకాలను కనుగొనగలను, ప్రయోజనాలను వివరించగలను మరియు దరఖాస్తు ప్రక్రియలను అర్థం చేసుకోవడంలో సహాయపడగలను.\n\nమీరు ఏది చేయాలనుకుంటున్నారు:\n- మీ వివరాలతో కూడిన ఫారమ్‌ను పూరించండి (సిఫార్సు చేయబడింది)\n- ఇక్కడే నాతో నేరుగా చాట్ చేయండి\n\nదయచేసి ఎంచుకోండి: 'ఫారమ్ పూరించు' లేదా 'చాట్ చేయి'",

        "phone_prompt": "మీ ఫోన్ నంబర్ ఏమిటి? (10 అంకెలు)",
        "phone_invalid": "దయచేసి సరైన 10 అంకెల ఫోన్ నంబర్‌ను నమోదు చేయండి.",
        "welcome": "తిరిగి స్వాగతం, {name}! వెల్ఫేర్‌బాట్ మీకు సహాయం చేయడానికి ఎల్లప్పుడూ ఇక్కడే ఉంటుంది. మీరు ఏ భాషలో కొనసాగించాలనుకుంటున్నారు?",
        "pin_setup": "వెల్ఫేర్‌బాట్‌తో కొనసాగడానికి, భద్రతా కారణాల దృష్ట్యా మీరు 4-అంకెల పిన్‌ను సెటప్ చేయాలి.",
        "pin_enter": "వెల్ఫేర్‌బాట్‌లోకి విజయవంతంగా ప్రవేశించడానికి, దయచేసి మీ పిన్‌ను నమోదు చేయండి.",
        "pin_confirm": "మీ పిన్‌ను నిర్ధారించండి",
        "pin_saved": "✅ మీ పిన్ సేవ్ చేయబడింది! దీనిని ఎవరితోనూ పంచుకోవద్దు.",
        "welcome_bot": "మిమ్మల్ని కలవడం చాలా సంతోషంగా ఉంది, {name}! WelfareBot కు స్వాగతం. మీ రాష్ట్రం, వృత్తి, ఆదాయం వంటి వివరాల ఆధారంగా మీరు అర్హులైన ప్రభుత్వ సంక్షేమ పథకాలను కనుగొనడంలో నేను మీకు సహాయపడతాను. నేను మీ గురించి కొంచెం తెలుసుకున్న తర్వాత, మీకు సరిపోయే ప్రతి పథకాన్ని మీకు చూపుతాను మరియు ఎలా దరఖాస్తు చేయాలనే దానిపై ప్రశ్నలకు కూడా సమాధానం ఇస్తాను. (Draft)",
        "pin_consent": "మనం కొనసాగడానికి ముందు, దయచేసి ఒక 4-అంకెల పిన్‌ను సెటప్ చేయండి - ఇది మీ ఖాతా మరియు వివరాలను సురక్షితంగా ఉంచుతుంది. కొనసాగడానికి సిద్ధంగా ఉన్నారా? (Draft)",
        "welcome_back": "మిమ్మల్ని మళ్లీ చూడటం సంతోషంగా ఉంది, {name}! WelfareBot కు తిరిగి స్వాగతం. నేను మీ వివరాలను భద్రపరిచాను మరియు మీరు చివరిసారి చూసినప్పటి నుండి కొత్త పథకాలు అందుబాటులో ఉండవచ్చు. (Draft)",
        "proceed_chip": "✅ కొనసాగించండి",
        "not_now_chip": "ఇప్పుడు కాదు",
        "forgot_pin": "పిన్ మర్చిపోయారా?"
    },
    "ta": {
        "state_q": "நீங்கள் எந்த மாநிலத்தைச் சேர்ந்தவர்?",
        "occupation_q": "உங்கள் தொழில் என்ன? (மாணவர், விவசாயி, தினசரி கூலி, சுயதொழில், அரசு ஊழியர், மற்றவை)",
        "caste_category_q": "உங்கள் சாதிப் பிரிவு என்ன? (SC, ST, OBC, பொது, EWS)",
        "gender_q": "உங்கள் பாலினம் என்ன? (ஆண், பெண், மற்றவை)",
        "age_q": "உங்கள் வயது என்ன?",
        "income_bracket_q": "உங்கள் ஆண்டு குடும்ப வருமானம் என்ன?",
        "land_size_q": "உங்களுக்கு எவ்வளவு விவசாய நிலம் உள்ளது (ஏக்கரில்)? (இல்லை என்றால் 0 ஐ உள்ளிடவும்)",
        "email_q": "உங்கள் மின்னஞ்சல் முகவரி என்ன? (விருப்பத்தேர்வு - தவிர்க்க 'skip' என தட்டச்சு செய்யவும்)",
        "confirm_header": "தயவுசெய்து உங்கள் விவரங்களை உறுதிப்படுத்தவும்:\n\n",
        "confirm_name": "👤 **பெயர்**",
        "confirm_lang": "🗣️ **மொழி**",
        "confirm_lang_name": "Tamil (தமிழ்)",
        "confirm_state": "📍 **மாநிலம்**",
        "confirm_occup": "💼 **தொழில்**",
        "confirm_caste": "🏷️ **சாதிப் பிரிவு**",
        "confirm_gender": "🚻 **பாலினம்**",
        "confirm_age": "🎂 **வயது**",
        "confirm_income": "💰 **ஆண்டு வருமானம்**",
        "confirm_land": "🌾 **நில அளவு**",
        "confirm_email": "📧 **மின்னஞ்சல்**",
        "confirm_not_provided": "வழங்கப்படவில்லை",
        "confirm_acres": "ஏக்கர்",
        "confirm_question": "இந்தத் தகவல் சரியானதா? (ஆம்/இல்லை)",
        "yes": "ஆம்",
        "no": "இல்லை",
        "correct_prompt": "உங்கள் விவரங்கள் சரியானவையா என்பதை உறுதிப்படுத்தவும். 'ஆம்' அல்லது 'இல்லை' என்று பதிலளிக்கவும்.",
        "edit_which": "எந்த விவரத்தை திருத்த விரும்புகிறீர்கள்?",
        "edit_fields": ["பெயர்", "மாநிலம்", "தொழில்", "சாதிப் பிரிவு", "பாலினம்", "வயது", "வருமானப் பிரிவு", "நில அளவு", "மின்னஞ்சல்"],
        "edit_prompt": "திருத்துவதற்கு பின்வரும் புலங்களில் ஒன்றைத் தேர்ந்தெடுக்கவும்: பெயர், மாநிலம், தொழில், சாதிப் பிரிவு, பாலினம், வயது, வருமானப் பிரிவு, நில அளவு, அல்லது மின்னஞ்சல்.",
        "edit_new_val": "உங்களது புதிய தகவலை உள்ளிடவும்: ",
        "invalid_age": "தயவுசெய்து சரியான வயதை உள்ளிடவும் (1 முதல் 120 வரை).",
        "invalid_land": "தயவுசெய்து ஏக்கரில் சரியான நில அளவை உள்ளிடவும் (எ.கா. 0 அல்லது 2.5).",
        "invalid_email": "தயவுசெய்து சரியான மின்னஞ்சல் முகவரியை உள்ளிடவும் அல்லது தவிர்க்க 'skip' என தட்டச்சு செய்யவும்.",
        "chat_choice_prompt": "அரட்டையில் உங்கள் விவரங்களை சேகரிப்போம். நீங்கள் எந்த மாநிலத்தில் வசிக்கிறீர்கள்?",
        "form_choice_prompt": "நான் சுயவிவரப் படிவத்தைத் திறந்துள்ளேன். பொருத்தமான திட்டங்களை நான் கண்டறிய தயவுசெய்து உங்கள் விவரங்களை நிரப்பவும்.",
        "form_choice_fallback": "தொடர சுயவிவரப் படிவத்தை நிரப்பவும், அல்லது இங்கு கேள்விகளுக்குப் பதிலளிக்க 'அரட்டை செய்' என தட்டச்சு செய்யவும்.",
        "no_match": "பொருத்தமான திட்டங்கள் எதுவும் தற்போது காணப்படவில்லை. புதிய திட்டங்களுக்கு பின்னர் சரிபார்க்கவும்!",
        "found_matches": "உங்கள் சுயவிவரத்திற்குப் பொருத்தமான {count} திட்டங்களைக் கண்டறிந்துள்ளேன்! மேலும் அறிய ஒரு திட்டத்தைத் தேர்ந்தெடுக்கவும்:",
        "error_fetching": "திட்டங்களைப் பெறுவதில் தற்போது சிக்கல் உள்ளது. தயவுசெய்து பின்னர் மீண்டும் முயற்சிக்கவும்.",
        "skip_email_chip": "மின்னஞ்சலைத் தவிர்",
        "chat_instead_chip": "💬 அரட்டை செய்",
        "fill_form_chip": "📝 படிவத்தை நிரப்பு",
        "states": ["ஆந்திரப் பிரதேசம்", "தெலங்கானா", "டெல்லி", "மகாராஷ்டிரா", "தமிழ்நாடு"],
        "occupations": ["மாணவர்", "விவசாயி", "தினசரி கூலி", "சுயதொழில்", "அரசு ஊழியர்", "மற்றவை"],
        "castes": ["பொது", "OBC", "SC", "ST", "EWS"],
        "genders": ["ஆண்", "பெண்", "இதர"],
        "incomes": ["1 லட்சத்திற்கும் குறைவாக", "1-2.5 லட்சம்", "2.5-5 லட்சம்", "5-10 லட்சம்", "10 லட்சத்திற்கும் மேல்"],
        "lands": ["0 ஏக்கர்", "1-2 ஏக்கர்", "3-5 ஏக்கர்", "5+ ஏக்கர்"],
        "name_step_reply": "வணக்கம் {name}! 😊\n\nதொடர எந்த மொழியை விரும்புகிறீர்கள்?",
        "form_chat_intro": "அற்புதம்! நீங்கள் தகுதிபெறும் அரசு நலத்திட்டங்களைக் கண்டறிய உங்களுக்கு உதவ நான் இங்கு இருக்கிறேன்.\n\nஉங்கள் சுயவிவரத்தின் அடிப்படையில் திட்டங்களைக் கண்டறிந்து, பலன்களை விளக்கி, விண்ணப்ப முறைகளைப் புரிந்துகொள்ள உதவ முடியும்.\n\nநீங்கள் என்ன செய்ய விரும்புகிறீர்கள்:\n- உங்கள் விவரங்களுடன் ஒரு படிவத்தை நிரப்பவும் (பரிந்துரைக்கப்படுகிறது)\n- என்னுடன் நேரடியாக இங்கேயே அரட்டை அடிக்கவும்\n\nதயவுசெய்து தேர்ந்தெடுக்கவும்: 'படிவத்தை நிரப்பு' அல்லது 'அரட்டை செய்'",

        "phone_prompt": "உங்கள் தொலைபேசி எண் என்ன? (10 இலக்கங்கள்)",
        "phone_invalid": "சரியான 10 இலக்க தொலைபேசி எண்ணை உள்ளிடவும்.",
        "welcome": "மீண்டும் வருக, {name}! உங்களுக்கு உதவ வெல்ஃபேர்பாட் எப்போதும் உள்ளது. நீங்கள் எந்த மொழியில் தொடர விரும்புகிறீர்கள்?",
        "pin_setup": "வெல்ஃபேர்பாட்டுடன் தொடர, பாதுகாப்பு காரணங்களுக்காக 4 இலக்க பின்னமைப்பை நீங்கள் அமைக்க வேண்டும்.",
        "pin_enter": "வெல்ஃபேர்பாட்டில் வெற்றிகரமாக நுழைய, உங்கள் பின்னை உள்ளிடவும்.",
        "pin_confirm": "உங்கள் பின்னை உறுதிப்படுத்தவும்",
        "pin_saved": "✅ உங்கள் பின் சேமிக்கப்பட்டது! இதை யாருடனும் பகிர வேண்டாம்.",
        "welcome_bot": "உங்களைச் சந்திப்பதில் மிகவும் மகிழ்ச்சி, {name}! WelfareBot க்கு உங்களை வரவேற்கிறேன். உங்கள் மாநிலம், தொழில், வருமானம் போன்ற விவரங்களின் அடிப்படையில் நீங்கள் தகுதிபெறும் அரசு நலத்திட்டங்களைக் கண்டறிய நான் உங்களுக்கு வழிகாட்டுவேன். உங்களைப் பற்றி நான் தெரிந்துகொண்டவுடன், உங்களுக்குப் பொருத்தமான ஒவ்வொரு திட்டத்தையும் நான் உங்களுக்குக் காண்பிப்பேன், மேலும் எவ்வாறு விண்ணப்பிப்பது என்ற கேள்விகளுக்கும் நான் பதிலளிப்பேன். (Draft)",
        "pin_consent": "நாம் தொடர்வதற்கு முன், 4 இலக்க பின்னை அமைக்கும்படி நான் உங்களைக் கேட்டுக்கொள்கிறேன் - இது உங்கள் கணக்கையும் விவரங்களையும் பாதுகாப்பாக வைத்திருக்கும். தொடரத் தயாரா? (Draft)",
        "welcome_back": "உங்களை மீண்டும் சந்திப்பதில் மகிழ்ச்சி, {name}! WelfareBot க்கு மீண்டும் வரவேற்கிறோம். நான் உங்கள் விவரங்களைச் சேமித்து வைத்துள்ளேன், நீங்கள் கடைசியாகப் பார்த்ததிலிருந்து புதிய திட்டங்கள் கிடைக்கக்கூடும். (Draft)",
        "proceed_chip": "✅ தொடர்க",
        "not_now_chip": "இப்போது வேண்டாம்",
        "forgot_pin": "பின் மறந்துவிட்டதா?"
    },
    "kn": {
        "state_q": "ನೀವು ಯಾವ ರಾಜ್ಯದವರು?",
        "occupation_q": "ನಿಮ್ಮ ಉದ್ಯೋಗವೇನು? (ವಿದ್ಯಾರ್ಥಿ, ರೈತು, ದಿನಗೂಲಿ ನೌಕರ, ಸ್ವಯಂ ಉದ್ಯೋಗಿ, ಸರ್ಕಾರಿ ನೌಕರ, ಇತರ)",
        "caste_category_q": "ನಿಮ್ಮ ಜಾತಿ ವರ್ಗ ಯಾವುದು? (SC, ST, OBC, ಸಾಮಾನ್ಯ, EWS)",
        "gender_q": "ನಿಮ್ಮ ಲಿಂಗ ಯಾವುದು? (ಪುರುಷ, ಮಹಿಳೆ, ಇತರ)",
        "age_q": "ನಿಮ್ಮ ವಯಸ್ಸು ಎಷ್ಟು?",
        "income_bracket_q": "ನಿಮ್ಮ ವಾರ್ಷಿಕ ಕೌಟುಂಬಿಕ ಆದಾಯ ಎಷ್ಟು?",
        "land_size_q": "ನಿಮ್ಮ ಒಡೆತನದಲ್ಲಿ ಎಷ್ಟು ಕೃಷಿ ಭೂಮಿ ಇದೆ (ಎಕರೆಗಳಲ್ಲಿ)? (ಯಾವುದೂ ಇಲ್ಲದಿದ್ದರೆ 0 ನಮೂದಿಸಿ)",
        "email_q": "ನಿಮ್ಮ ಇಮೇಲ್ ವಿಳಾಸವೇನು? (ಐಚ್ಛಿಕ - ಬಿಡಲು 'skip' ಎಂದು ಟೈಪ್ ಮಾಡಿ)",
        "confirm_header": "ದಯವಿಟ್ಟು ನಿಮ್ಮ ವಿವರಗಳನ್ನು ಖಚಿತಪಡಿಸಿ:\n\n",
        "confirm_name": "👤 **ಹೆಸರು**",
        "confirm_lang": "🗣️ **ಭಾಷೆ**",
        "confirm_lang_name": "Kannada (ಕನ್ನಡ)",
        "confirm_state": "📍 **ರಾಜ್ಯ**",
        "confirm_occup": "💼 **ಉದ್ಯೋಗ**",
        "confirm_caste": "🏷️ **ಜಾತಿ ವರ್ಗ**",
        "confirm_gender": "🚻 **ಲಿಂಗ**",
        "confirm_age": "🎂 **ವಯಸ್ಸು**",
        "confirm_income": "💰 **ವಾರ್ಷಿಕ ಆದಾಯ**",
        "confirm_land": "🌾 **ಭೂಮಿಯ ಗಾತ್ರ**",
        "confirm_email": "📧 **ಇಮೇಲ್**",
        "confirm_not_provided": "ಒದಗಿಸಲಾಗಿಲ್ಲ",
        "confirm_acres": "ಎಕರೆ",
        "confirm_question": "ಈ ಮಾಹಿತಿ ಸರಿಯಾಗಿದೆಯೇ? (ಹೌದು/ಅಲ್ಲ)",
        "yes": "ಹೌದು",
        "no": "ಅಲ್ಲ",
        "correct_prompt": "ನಿಮ್ಮ ವಿವರಗಳು ಸರಿಯಾಗಿದೆಯೇ ಎಂದು ಖಚಿತಪಡಿಸಿ. 'ಹೌದು' ಅಥವಾ 'ಅಲ್ಲ' ಎಂದು ಉತ್ತರಿಸಿ.",
        "edit_which": "ನೀವು ಯಾವ ವಿವರವನ್ನು ತಿದ್ದುಪಡಿ ಮಾಡಲು ಬಯಸುತ್ತೀರಿ?",
        "edit_fields": ["ಹೆಸರು", "ರಾಜ್ಯ", "ಉದ್ಯೋಗ", "ಜಾತಿ ವರ್ಗ", "ಲಿಂಗ", "ವಯಸ್ಸು", "ಆದಾಯ ಶ್ರೇಣಿ", "ಭೂಮಿಯ ಗಾತ್ರ", "ಇಮೇಲ್"],
        "edit_prompt": "ತಿದ್ದುಪಡಿ ಮಾಡಲು ಈ ಕೆಳಗಿನ ಕ್ಷೇತ್ರಗಳಲ್ಲಿ ಒಂದನ್ನು ಆಯ್ಕೆಮಾಡಿ: ಹೆಸರು, ರಾಜ್ಯ, ಉದ್ಯೋಗ, ಜಾತಿ ವರ್ಗ, ಲಿಂಗ, ವಯಸ್ಸು, ಆದಾಯ ಶ್ರೇಣಿ, ಭೂಮಿಯ ಗಾತ್ರ, ಅಥವಾ ಇಮೇಲ್.",
        "edit_new_val": "ದಯವಿಟ್ಟು ನಿಮ್ಮ ಹೊಸ ವಿವರವನ್ನು ನಮೂದಿಸಿ: ",
        "invalid_age": "ದಯವಿಟ್ಟು ಮಾನ್ಯವಾದ ವಯಸ್ಸನ್ನು ನಮೂದಿಸಿ (1 ರಿಂದ 120 ರವರೆಗೆ).",
        "invalid_land": "ದಯವಿಟ್ಟು ಎಕರೆಗಳಲ್ಲಿ ಮಾನ್ಯವಾದ ಭೂಮಿಯ ಗಾತ್ರವನ್ನು ನಮೂದಿಸಿ (ಉದಾ. 0 ಅಥವಾ 2.5).",
        "invalid_email": "ದಯವಿಟ್ಟು ಮಾನ್ಯವಾದ ಇಮೇಲ್ ವಿಳಾಸವನ್ನು ನಮೂದಿಸಿ ಅಥವಾ ಬಿಡಲು 'skip' ಎಂದು ಟೈಪ್ ಮಾಡಿ.",
        "chat_choice_prompt": "ಚಾಟ್‌ನಲ್ಲಿ ನಿಮ್ಮ ವಿವರಗಳನ್ನು ಸಂಗ್ರಹಿಸೋಣ. ನೀವು ಯಾವ ರಾಜ್ಯದಲ್ಲಿ ವಾಸಿಸುತ್ತಿದ್ದೀರಿ?",
        "form_choice_prompt": "ನಾನು ಪ್ರೊಫೈಲ್ ಫಾರ್ಮ್ ಅನ್ನು ತೆರೆದಿದ್ದೇನೆ. ಸೂಕ್ತವಾದ ಯೋಜನೆಗಳನ್ನು ನಾನು ಹುಡುಕಲು ದಯವಿಟ್ಟು ನಿಮ್ಮ ವಿವರಗಳನ್ನು ಭರ್ತಿ ಮಾಡಿ.",
        "form_choice_fallback": "ಮುಂದುವರಿಯಲು ಪ್ರೊಫೈಲ್ ಫಾರ್ಮ್ ಭರ್ತಿ ಮಾಡಿ, ಅಥವಾ ಇಲ್ಲಿ ಪ್ರಶ್ನೆಗಳಿಗೆ ಉತ್ತರಿಸಲು 'ಚಾಟ್ ಮಾಡಿ' ಎಂದು ಟೈಪ್ ಮಾಡಿ.",
        "no_match": "ಪ್ರಸ್ತುತ ಯಾವುದೇ ಯೋಜನೆಗಳು ಕಂಡುಬಂದಿಲ್ಲ. ಹೊಸ ಯೋಜನೆಗಳಿಗಾಗಿ ನಂತರ ಪರಿಶೀಲಿಸಿ!",
        "found_matches": "ನಿಮ್ಮ ಪ್ರೊಫೈಲ್‌ಗೆ ಹೊಂದುವ {count} ಯೋಜನೆಗಳನ್ನು ನಾನು ಕಂಡುಹಿಡಿದಿದ್ದೇನೆ! ವಿವರಗಳಿಗಾಗಿ ಯೋಜನೆಯನ್ನು ಆಯ್ಕೆಮಾಡಿ:",
        "error_fetching": "ಯೋಜನೆಗಳನ್ನು ಹಿಂಪಡೆಯುವಲ್ಲಿ ಪ್ರಸ್ತುತ ಸಮಸ್ಯೆಯಿದೆ. ದಯವಿಟ್ಟು ನಂತರ ಪ್ರಯತ್ನಿಸಿ.",
        "skip_email_chip": "ಇಮೇಲ್ ಬಿಟ್ಟುಬಿಡಿ",
        "chat_instead_chip": "💬 ಚಾಟ್ ಮಾಡಿ",
        "fill_form_chip": "📝 ಫಾರ್ಮ್ ಭರ್ತಿಮಾಡಿ",
        "states": ["ಆಂಧ್ರ ಪ್ರದೇಶ", "ತೆಲಂಗಾಣ", "ದೆಹಲಿ", "ಮಹಾರಾಷ್ಟ್ರ", "ತಮಿಳುನಾಡು"],
        "occupations": ["ವಿದ್ಯಾರ್ಥಿ", "ರೈತು", "ದಿನಗೂಲಿ ನೌಕರ", "ಸ್ವಯಂ ಉದ್ಯೋಗಿ", "ಸರ್ಕಾರಿ ನೌಕರ", "ಇತರ"],
        "castes": ["ಸಾಮಾನ್ಯ", "OBC", "SC", "ST", "EWS"],
        "genders": ["ಪುರುಷ", "ಮಹಿಳೆ", "ಇತರ"],
        "incomes": ["1 ಲಕ್ಷಕ್ಕಿಂತ ಕಡಿಮೆ", "1-2.5 ಲಕ್ಷ", "2.5-5 ಲಕ್ಷ", "5-10 ಲಕ್ಷ", "10 ಲಕ್ಷಕ್ಕಿಂತ ಹೆಚ್ಚು"],
        "lands": ["0 ಎಕರೆ", "1-2 ಎಕರೆ", "3-5 ಎಕರೆ", "5+ ಎಕರೆ"],
        "name_step_reply": "ನಮಸ್ಕಾರ {name}! 😊\n\nಮುಂದುವರಿಯಲು ಯಾವ ಭಾಷೆಯನ್ನು ಬಯಸುತ್ತೀರಿ?",
        "form_chat_intro": "ಅದ್ಭುತ! ನೀವು ಅರ್ಹತೆ ಹೊಂದಿರುವ ಸರ್ಕಾರಿ ಕಲ್ಯಾಣ ಯೋಜನೆಗಳನ್ನು ಅನ್ವೇಷಿಸಲು ನಾನು ನಿಮಗೆ ಸಹಾಯ ಮಾಡುತ್ತೇನೆ.\n\nನಿಮ್ಮ ಪ್ರೊಫೈಲ್ ಆಧಾರದ ಮೇಲೆ ಯೋಜನೆಗಳನ್ನು ಹುಡುಕಬಹುದು, ಪ್ರಯೋಜನಗಳನ್ನು ವಿವರಿಸಬಹುದು ಮತ್ತು ಅರ್ಜಿ ಸಲ್ಲಿಸುವ ವಿಧಾನವನ್ನು ಅರ್ಥಮಾಡಿಕೊಳ್ಳಲು ಸಹಾಯ ಮಾಡುತ್ತೇನೆ.\n\nನೀವು ಏನು ಮಾಡಲು ಬಯಸುತ್ತೀರಿ:\n- ನಿಮ್ಮ ವಿವರಗಳೊಂದಿಗೆ ಫಾರ್ಮ್ ಭರ್ತಿ ಮಾಡಿ (ಶಿಫಾರಸು ಮಾಡಲಾಗಿದೆ)\n- ನನ್ನೊಂದಿಗೆ ನೇರವಾಗಿ ಇಲ್ಲೇ ಚಾಟ್ ಮಾಡಿ\n\nದಯವಿಟ್ಟು ಆಯ್ಕೆಮಾಡಿ: 'ಫಾರ್ಮ್ ಭರ್ತಿಮಾಡಿ' ಅಥವಾ 'ಚಾಟ್ ಮಾಡಿ'",
        "welcome_bot": "ನಿಮ್ಮನ್ನು ಭೇಟಿಯಾಗಲು ತುಂಬಾ ಸಂತೋಷವಾಗಿದೆ, {name}! WelfareBot ಗೆ ಸ್ವಾಗತ. ನಿಮ್ಮ ರಾಜ್ಯ, ಉದ್ಯೋಗ, ಆದಾಯ ಮುಂತಾದ ವಿವರಗಳ ಆಧಾರದ ಮೇಲೆ ನೀವು ಅರ್ಹರಾಗಿರುವ ಸರ್ಕಾರಿ ಕಲ್ಯಾಣ ಯೋಜನೆಗಳನ್ನು ಹುಡುಕಲು ನಾನು ನಿಮಗೆ ಮಾರ್ಗದರ್ಶನ ನೀಡುತ್ತೇನೆ. ನಿಮ್ಮ ಬಗ್ಗೆ ನಾನು ಸ್ವಲ್ಪ ತಿಳಿದುಕೊಂಡ ನಂತರ, ನಿಮಗೆ ಹೊಂದುವ ಪ್ರತಿಯೊಂದು ಯೋಜನೆಯನ್ನು ನಾನು ನಿಮಗೆ ತೋರಿಸುತ್ತೇನೆ ಮತ್ತು ಹೇಗೆ ಅರ್ಜಿ ಸಲ್ಲಿಸಬೇಕು ಎಂಬ ಪ್ರಶ್ನೆಗಳಿಗೆ ಉತ್ತರಿಸುತ್ತೇನೆ. (Draft)",
        "pin_consent": "ನಾವು ಮುಂದುವರಿಯುವ ಮೊದಲು, 4-ಅಂಕಿಯ ಪಿನ್ ಅನ್ನು ಹೊಂದಿಸಲು ನಾನು ನಿಮ್ಮನ್ನು ಕೇಳುತ್ತೇನೆ - ಇದು ನಿಮ್ಮ ಖಾತೆ ಮತ್ತು ವಿವರಗಳನ್ನು ಸುರಕ್ಷಿತವಾಗಿರಿಸುತ್ತದೆ. ಮುಂದುವರಿಯಲು ಸಿದ್ಧರಿದ್ದೀರಾ? (Draft)",
        "welcome_back": "ನಿಮ್ಮನ್ನು ಮತ್ತೆ ನೋಡಿ ಸಂತೋಷವಾಯಿತು, {name}! WelfareBot ಗೆ ಮತ್ತೆ ಸ್ವಾಗತ. ನಾನು ನಿಮ್ಮ ವಿವರಗಳನ್ನು ಉಳಿಸಿದ್ದೇನೆ ಮತ್ತು ನೀವು ಕೊನೆಯ ಬಾರಿಗೆ ಪರಿಶೀಲಿಸಿದ ನಂತರ ಹೊಸ ಯೋಜನೆಗಳು ಲಭ್ಯವಿರಬಹುದು. (Draft)",
        "proceed_chip": "✅ ಮುಂದುವರಿಯಿರಿ",
        "not_now_chip": "ಈಗ ಬೇಡ",
        "forgot_pin": "ಪಿನ್ ಮರೆತಿರಾ?"
    }
}

def normalize_lang_code(val: str) -> str:
    if not val:
        return "en"
    val = val.lower().strip()
    if val in ["te", "telugu", "తెలుగు"]:
        return "te"
    if val in ["hi", "hindi", "हिंदी"]:
        return "hi"
    if val in ["ta", "tamil", "தமிழ்"]:
        return "ta"
    if val in ["kn", "kannada", "ಕನ್ನಡ"]:
        return "kn"
    return "en"

def get_trans(lang_code: str) -> dict:
    code = normalize_lang_code(lang_code)
    return ONBOARDING_TRANSLATIONS.get(code, ONBOARDING_TRANSLATIONS["en"])

def normalize_to_english(field: str, val: str, user_lang: str) -> str:
    """Normalize a translated value to its English counterpart based on parallel lists in translations."""
    if not val:
        return val
        
    field_to_key = {
        "state": "states",
        "occupation": "occupations",
        "caste_category": "castes",
        "gender": "genders",
        "income_bracket": "incomes",
        "land_size": "lands"
    }
    
    key = field_to_key.get(field)
    if not key:
        return val
        
    lang_code = normalize_lang_code(user_lang)
    
    # Get the list for the user's language and the English list
    user_list = ONBOARDING_TRANSLATIONS.get(lang_code, {}).get(key, [])
    en_list = ONBOARDING_TRANSLATIONS["en"].get(key, [])
    
    val_clean = val.strip().lower()
    for idx, item in enumerate(user_list):
        if item.strip().lower() == val_clean:
            if idx < len(en_list):
                return en_list[idx]
                
    # Also check if it's already in the English list
    for idx, item in enumerate(en_list):
        if item.strip().lower() == val_clean:
            return item
            
    # Check partial matches
    for idx, item in enumerate(user_list):
        if val_clean in item.strip().lower() or item.strip().lower() in val_clean:
            if idx < len(en_list):
                return en_list[idx]
                
    return val

def denormalize_from_english(field: str, val: str, target_lang: str) -> str:
    """Translate an English value back to the target language preference."""
    if not val:
        return val
        
    field_to_key = {
        "state": "states",
        "occupation": "occupations",
        "caste_category": "castes",
        "gender": "genders",
        "income_bracket": "incomes",
        "land_size": "lands"
    }
    
    key = field_to_key.get(field)
    if not key:
        return val
        
    lang_code = normalize_lang_code(target_lang)
    if lang_code == "en":
        return val
        
    user_list = ONBOARDING_TRANSLATIONS.get(lang_code, {}).get(key, [])
    en_list = ONBOARDING_TRANSLATIONS["en"].get(key, [])
    
    val_clean = val.strip().lower()
    for idx, item in enumerate(en_list):
        if item.strip().lower() == val_clean:
            if idx < len(user_list):
                return user_list[idx]
                
    # Check if it is already in the user list
    for idx, item in enumerate(user_list):
        if item.strip().lower() == val_clean:
            return item
            
    return val

def generate_profile_summary(user_doc: dict) -> str:
    lang = user_doc.get("language_preference", "en")
    trans = get_trans(lang)
    
    # Translate stored English values back to selected language
    state_disp = denormalize_from_english("state", user_doc.get("state"), lang)
    occupation_disp = denormalize_from_english("occupation", user_doc.get("occupation"), lang)
    caste_disp = denormalize_from_english("caste_category", user_doc.get("caste_category"), lang)
    gender_disp = denormalize_from_english("gender", user_doc.get("gender"), lang)
    income_disp = denormalize_from_english("income_bracket", user_doc.get("income_bracket"), lang)
    land_disp = denormalize_from_english("land_size", user_doc.get("land_size", "0"), lang)
    
    summary = (
        f"{trans['confirm_name']}: {user_doc.get('name')}\n"
        f"{trans['confirm_lang']}: {trans['confirm_lang_name']}\n"
        f"{trans['confirm_state']}: {state_disp}\n"
        f"{trans['confirm_occup']}: {occupation_disp}\n"
        f"{trans['confirm_caste']}: {caste_disp}\n"
        f"{trans['confirm_gender']}: {gender_disp}\n"
        f"{trans['confirm_age']}: {user_doc.get('age')}\n"
        f"{trans['confirm_income']}: {income_disp}\n"
        f"{trans['confirm_land']}: {land_disp}\n"
        f"{trans['confirm_email']}: {user_doc.get('email') or trans['confirm_not_provided']}"
    )
    return summary


# ---------- Constants ----------
REQUIRED_FIELDS = [
    "name",
    "language_preference",
    "state",
    "occupation",
    "caste_category",
    "gender",
    "age",
    "income_bracket",
    "land_size",
    "email",
]

SCHEME_KEYWORDS = [
    "scheme",
    "eligible",
    "scholarship",
    "benefit",
    "welfare",
    "apply",
    "government",
    "subsidy",
    "yojana",
    "assistance",
]

# ---------- Helper Functions ----------
# Common greeting/filler words that should never be mistaken for a name
GREETING_WORDS = {
    "hi", "hii", "hiii", "hello", "helo", "hlo", "hey", "heya",
    "hola", "namaste", "yo", "sup", "greetings"
}

def extract_name(message: str) -> str:
    """
    Robustly extracts a name from natural sentences using Groq LLM.
    """
    message = message.strip()
    if not message:
        return ""

    # Call Groq for extraction
    messages = [
        {"role": "system", "content": "You are a precise name extraction tool. Extract only the person's first name from the user's message. Output ONLY the name, nothing else. If there is no name present, output exactly the word: NONE."},
        {"role": "user", "content": message}
    ]
    
    extracted = safe_groq_chat(messages, temperature=0.0).strip()
    
    if not extracted or extracted.upper() == "NONE":
        return ""
        
    # Clean up (remove punctuation, etc.) just in case Groq added a period
    extracted = re.sub(r'[^\w\s]', '', extracted).split()[0]
    return extracted.capitalize()

def safe_groq_chat(messages: List[Dict[str, str]], temperature: float = 0.7) -> str:
    """Call Groq chat completion with retries and timeout.
    Returns the response text or an empty string on failure.
    """
    max_retries = 2
    for attempt in range(1, max_retries + 1):
        try:
            resp = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                temperature=temperature,
                timeout=10,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Groq chat error (attempt {attempt}): {e}")
            if attempt == max_retries:
                return ""
    return ""

def calculate_confidence(message: str, intent: str, user_profile: dict) -> float:
    """Calculate confidence score for a query based on various factors.
    Returns a float between 0.0 and 1.0.
    """
    score = 0.5  # Base confidence
    
    # Boost confidence for clear intent
    if intent == "scheme_query":
        # Check if profile is complete
        required_fields = ["state", "occupation", "caste_category", "gender", "age", "income_bracket"]
        profile_complete = all(user_profile.get(f) for f in required_fields)
        if profile_complete:
            score += 0.3
        else:
            score -= 0.2
    
    # Boost for longer, more detailed messages
    if len(message) > 20:
        score += 0.1
    if len(message) > 50:
        score += 0.1
    
    # Boost for scheme-related keywords
    scheme_keywords = ["scheme", "benefit", "subsidy", "government", "apply", "eligibility"]
    if any(kw in message.lower() for kw in scheme_keywords):
        score += 0.2
    
    # Reduce confidence for very short messages
    if len(message) < 5:
        score -= 0.3
    
    # Ensure score is between 0 and 1
    return max(0.0, min(1.0, score))

# ---------- Intent Detection & Handlers ----------
def detect_intent(state: Dict[str, Any]) -> Dict[str, Any]:
    """Determine user intent for routing.
    Updates `state["intent"]`.
    """
    message = state.get("message", "").strip()
    session_id = state["session_id"]
    message_lower = message.lower()
    
    # Check for restart
    if message_lower in ["start over", "start_over", "restart", "reset"]:
        sync_users_collection.delete_one({"session_id": session_id})
        state["user_profile"] = {}
        state["intent"] = "onboarding"
        state["reply"] = "Welcome to WelfareBot! I help Indian citizens discover government welfare schemes they're eligible for.|||To get started, could you tell me your name?"
        state["chips"] = ["Start Over"]
        state["onboarding_step"] = "name"
        state["clear_session"] = True
        state["confidence_score"] = 100
        return state

    user_doc = sync_users_collection.find_one({"session_id": session_id}) or {}
    state["user_profile"] = user_doc
    current_step = user_doc.get("onboarding_step", "name")
    
    # Check for change language request
    change_lang_patterns = [
        "change language", "change my language", "language preference", "select language", "different language",
        "भाषा बदलें", "भाषा बदलो", "लैंग्वेज चेंज",
        "భాష మార్చండి", "భాషను మార్చండి", "భాష మార్చు",
        "மொழியை மாற்று", "மொழி மாற்றம்",
        "ಭಾಷೆ ಬದಲಾಯಿಸಿ", "ಭಾಷೆಯನ್ನು ಬದಲಾಯಿಸಿ"
    ]
    if any(p in message_lower for p in change_lang_patterns):
        prev_step = user_doc.get("onboarding_step", "name")
        # Check to avoid loop if already in language preference step
        if prev_step != "language_preference":
            sync_users_collection.update_one(
                {"session_id": session_id},
                {"$set": {"onboarding_step": "language_preference", "prev_onboarding_step": prev_step}}
            )
            state["intent"] = "change_lang"
            state["onboarding_step"] = "language_preference"
            state["reply"] = "Which language would you prefer? / आप कौन सी भाषा पसंद करेंगे? / మీరు ఏ భాషను ఇష్టపడతారు?"
            state["chips"] = ["English", "हिंदी", "తెలుగు", "தமிழ்", "ಕನ್ನಡ"]
            state["confidence_score"] = 100
            return state
    
    reminder_patterns = ["remind me", "set reminder", "schedule reminder", "reminder"]
    if any(p in message_lower for p in reminder_patterns):
        state["intent"] = "schedule_reminder"
        logger.info(f"detect_intent -> intent: schedule_reminder | session: {session_id} | msg: '{message}'")
        return state

    if current_step != "complete":
        state["intent"] = "onboarding"
    else:
        more_schemes_patterns = ["more schemes", "show more schemes", "మరిన్ని పథకాలు", "और योजनाएं", "மேலும் திட்டங்கள்", "ಹೆಚ್ಚಿನ ಯೋಜನೆಗಳು"]
        if any(p == message_lower for p in more_schemes_patterns):
            state["intent"] = "scheme_query"
            state["show_more_schemes"] = True
        else:
            state["intent"] = "faq"
        
    logger.info(f"detect_intent -> intent: {state['intent']} | step: {current_step} | session: {session_id} | msg: '{message}'")
    return state


def extract_phone(message: str) -> str:
    digits = re.sub(r'\D', '', message)
    if len(digits) == 12 and digits.startswith("91"):
        return digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        return digits[1:]
    elif len(digits) == 10:
        return digits
    return ""

import hashlib
def hash_pin(pin: str) -> str:
    return hashlib.sha256(pin.encode()).hexdigest()

def handle_onboarding(state: Dict[str, Any]) -> Dict[str, Any]:
    """Collect missing profile fields step‑by‑step."""
    state["confidence_score"] = 100
    if state.get("clear_session"):
        return state

    session_id = state["session_id"]
    message = state["message"].strip()
    user_doc = sync_users_collection.find_one({"session_id": session_id}) or {}
    current_step = user_doc.get("onboarding_step", "name")
    
    lang = user_doc.get("language_preference", "en")
    trans = get_trans(lang)

    # Helper to persist step
    def update_profile(updates: Dict[str, Any]):
        sync_users_collection.update_one(
            {"session_id": session_id},
            {"$set": updates},
            upsert=True,
        )

    # STEP 1 - name extraction
    if current_step == "name":
        name = extract_name(message)
        if not name:
            state["reply"] = "Sorry, I couldn't catch your name. Could you tell me your name again? 😊"
            return state
        update_profile({"name": name, "onboarding_step": "phone_number"})
        state["reply"] = f"Nice to meet you, {name}! Could you share your 10-digit phone number? This helps me check if you already have an account with us."
        state["onboarding_step"] = "phone_number"
        return state

    # STEP 1.5 - Phone number
    if current_step == "phone_number":
        phone = extract_phone(message)
        if not phone:
            state["reply"] = "That doesn't look like a valid 10-digit number — could you try again?"
            return state
        
        # Check if user already exists
        existing = sync_users_collection.find_one({
            "phone_number": phone,
            "name": user_doc.get("name")
        })
        if existing and existing.get("pin"):
            # Merge existing profile to current session
            update_data = {k: v for k, v in existing.items() if k not in ["_id", "session_id"]}
            update_data["is_returning"] = True
            update_data["onboarding_step"] = "login_pin"
            
            # Reset only if lockout is expired
            lockout_until = existing.get("pin_lockout_until")
            from datetime import datetime
            if lockout_until and datetime.utcnow().isoformat() >= lockout_until:
                update_data["failed_pin_attempts"] = 0
                update_data["pin_lockout_until"] = None
                lockout_until = None
                
            update_profile(update_data)
            
            user_name = existing.get("name", user_doc.get("name", "Friend"))
            lang_pref = existing.get("language_preference", "en")
            trans_existing = get_trans(lang_pref)
            
            welcome_msg = trans_existing.get("welcome_back", "Good to see you again, {name}! Welcome back to WelfareBot. I've got your details saved, and there may be new schemes available since you last checked.").replace("{name}", user_name)
            state["reply"] = welcome_msg + "|||" + "Please enter your PIN to continue."
            state["onboarding_step"] = "login_pin"
            state["show_pin_popup"] = True
            state["pin_mode"] = "login"
            if lockout_until:
                state["pin_lockout_until"] = lockout_until
            return state
        
        # New account creation (if name + phone combo doesn't exist)
        update_profile({"phone_number": phone, "onboarding_step": "language_preference", "is_returning": False})

        state["reply"] = "Which language would you like to continue in?"
        state["chips"] = ["English", "हिंदी", "తెలుగు", "தமிழ்", "ಕನ್ನಡ"]
        state["onboarding_step"] = "language_preference"
        return state

    # STEP 2 - language
    if current_step == "language_preference":
        lang_map = {
            "hindi": "hi", "हिंदी": "hi",
            "telugu": "te", "తెలుగు": "te",
            "tamil": "ta", "தமிழ்": "ta",
            "kannada": "kn", "ಕನ್ನಡ": "kn",
        }
        lower_msg = message.lower()
        lang = "en"
        for key, code in lang_map.items():
            if key in lower_msg:
                lang = code
                break
        
        trans = get_trans(lang)
        update_profile({"language_preference": lang, "onboarding_step": "pin_consent"})
        
        user_name = user_doc.get("name", "Friend")
        welcome_bot = trans.get("welcome_bot", "It's wonderful to meet you, {name}! Welcome to WelfareBot.\n\nI'm here to guide you through finding government welfare schemes you're eligible for — based on details like your state, occupation, income, and a few other things. Once I know a bit about you, I'll show you every scheme that matches, and I can also answer questions about how to apply.").replace("{name}", user_name)
        pin_consent = trans.get("pin_consent", "Before we continue, I'll ask you to set up a 4-digit PIN — this keeps your account and details secure. Ready to proceed?")
        
        state["reply"] = welcome_bot + "|||" + pin_consent
        state["onboarding_step"] = "pin_consent"
        state["chips"] = [trans.get("proceed_chip", "✅ Proceed"), trans.get("not_now_chip", "Not now")]
        return state

    # STEP 2.05 - PIN Consent
    if current_step == "pin_consent":
        msg_clean = message.lower().strip()
        proceed_words = ["proceed", "yes", "ok", "ready", "✅", "आगे", "కొనసాగించండి", "தொடர்க", "ಮುಂದುವರಿಯಿರಿ"]
        not_now_words = ["not now", "no", "later", "अभी नहीं", "కాదు", "வேண்டாம்", "ಬೇಡ"]
        
        if any(w in msg_clean for w in proceed_words) or msg_clean == "continue":
            update_profile({"onboarding_step": "pin_setup"})
            state["reply"] = trans.get("pin_setup", "To keep your account secure, please set up a 4-digit PIN.")
            state["onboarding_step"] = "pin_setup"
            state["show_pin_popup"] = True
            state["pin_mode"] = "setup"
            return state
        elif any(w in msg_clean for w in not_now_words):
            state["reply"] = "No problem — just type 'continue' whenever you're ready to set up your PIN."
            state["chips"] = [trans.get("proceed_chip", "✅ Proceed")]
            return state
        else:
            state["reply"] = "Type 'continue' to set up your PIN, or select an option below."
            state["chips"] = [trans.get("proceed_chip", "✅ Proceed"), trans.get("not_now_chip", "Not now")]
            return state

    # STEP 2.1 - Login PIN (Returning Users)
    if current_step == "login_pin":
        import time
        from datetime import datetime
        
        if message.strip().lower() == "forgot_pin":
            update_profile({"onboarding_step": "forgot_pin_phone"})
            state["reply"] = "Please enter your 10-digit phone number to verify your identity."
            state["onboarding_step"] = "forgot_pin_phone"
            return state
            
        pin = message.strip().replace(" ", "")
        if len(pin) != 4 or not pin.isdigit():
            state["reply"] = "Please enter your 4-digit PIN."
            state["show_pin_popup"] = True
            state["pin_mode"] = "login"
            return state
            
        # Check lockout
        lockout_until = user_doc.get("pin_lockout_until")
        if lockout_until:
            if datetime.utcnow().isoformat() < lockout_until:
                state["reply"] = "Too many incorrect attempts. Please try again later."
                state["show_pin_popup"] = True
                state["pin_mode"] = "login"
                state["pin_lockout_until"] = lockout_until
                return state
            else:
                # Lockout expired, reset counter
                update_profile({"failed_pin_attempts": 0, "pin_lockout_until": None})
                user_doc["failed_pin_attempts"] = 0
                
        saved_pin = user_doc.get("pin")
        if hash_pin(pin) == saved_pin:
            update_profile({"onboarding_step": "confirmation", "confirmation_step": "awaiting_confirmation", "failed_pin_attempts": 0, "pin_lockout_until": None})
            
            # Sync back to all sessions with same name + phone
            sync_users_collection.update_many(
                {"phone_number": user_doc.get("phone_number"), "name": user_doc.get("name")},
                {"$set": {"failed_pin_attempts": 0, "pin_lockout_until": None}}
            )
            
            state["onboarding_step"] = "confirmation"
            state["confirmation_step"] = "awaiting_confirmation"
            state["reply"] = "Here are the details I have on file for you:\n\n" + generate_profile_summary(user_doc) + "|||\nAre these still correct?"
            state["chips"] = ["✅ Yes, still correct", "✏️ No, update details"]
            return state
        else:
            attempts = user_doc.get("failed_pin_attempts", 0) + 1
            if attempts >= 3:
                from datetime import timedelta
                lockout_time = (datetime.utcnow() + timedelta(minutes=5)).isoformat()
                update_profile({"failed_pin_attempts": attempts, "pin_lockout_until": lockout_time})
                
                # Sync lockout to all sessions with same name + phone
                sync_users_collection.update_many(
                    {"phone_number": user_doc.get("phone_number"), "name": user_doc.get("name")},
                    {"$set": {"failed_pin_attempts": attempts, "pin_lockout_until": lockout_time}}
                )
                
                state["reply"] = "Too many incorrect attempts. Please try again later."
                state["show_pin_popup"] = True
                state["pin_mode"] = "login"
                state["pin_lockout_until"] = lockout_time
                return state
            else:
                update_profile({"failed_pin_attempts": attempts})
                
                # Sync attempts to all sessions with same name + phone
                sync_users_collection.update_many(
                    {"phone_number": user_doc.get("phone_number"), "name": user_doc.get("name")},
                    {"$set": {"failed_pin_attempts": attempts}}
                )
                
                state["reply"] = "That PIN doesn't match — try again."
                state["show_pin_popup"] = True
                state["pin_mode"] = "login"
                return state

    # STEP 2.1.5 - Forgot PIN Phone Verification
    if current_step == "forgot_pin_phone":
        phone = extract_phone(message)
        if not phone:
            state["reply"] = "That doesn't look like a valid 10-digit number — could you try again?"
            return state
        if phone == user_doc.get("phone_number"):
            update_profile({"onboarding_step": "pin_setup"})
            state["reply"] = "Phone verified. Please set up a new 4-digit PIN."
            state["onboarding_step"] = "pin_setup"
            state["show_pin_popup"] = True
            state["pin_mode"] = "setup"
            return state
        else:
            state["reply"] = "That phone number does not match our records. Please try again or type 'Start Over' to create a new account."
            return state

    # STEP 2.2 - PIN Setup (New Users & Forgot PIN)
    if current_step == "pin_setup":
        pin = message.strip().replace(" ", "")
        if len(pin) != 4 or not pin.isdigit():
            state["reply"] = "Invalid PIN. " + trans.get("pin_setup", "Please set a 4-digit PIN.")
            state["show_pin_popup"] = True
            state["pin_mode"] = "setup"
            return state
            
        update_profile({
            "pin": hash_pin(pin),
            "onboarding_step": "form_chat_choice" if not user_doc.get("is_returning") else "confirmation"
        })
        
        if user_doc.get("is_returning"):
            update_profile({"confirmation_step": "awaiting_confirmation", "failed_pin_attempts": 0, "pin_lockout_until": None})
            state["onboarding_step"] = "confirmation"
            state["confirmation_step"] = "awaiting_confirmation"
            state["reply"] = "✅ Your new PIN is saved!\n\nHere are the details I have on file for you:\n\n" + generate_profile_summary(user_doc) + "\nAre these still correct?"
            state["chips"] = ["✅ Yes, still correct", "✏️ No, update details"]
        else:
            state["reply"] = trans.get("pin_success", "✅ PIN set successfully! Let's find your welfare schemes.") + "|||" + trans.get("form_chat_intro")
            state["chips"] = [trans.get("fill_form_chip", "📝 Fill Form"), trans.get("chat_instead_chip", "💬 Chat Instead")]
            state["onboarding_step"] = "form_chat_choice"
        return state

    # STEP 3 – Form or Chat choice
    if current_step == "form_chat_choice":
        msg_clean = message.lower().strip()
        is_form = any(w in msg_clean for w in [
            "form", "fill form", "📝 fill form", 
            "फ़ॉर्म भरें", "📝 फ़ॉर्म भरें", 
            "ఫారమ్ పూరించు", "📝 ఫారమ్ పూరించు", 
            "படிவத்தை நிரப்பு", "📝 படிவத்தை நிரப்பு", 
            "ಫಾರ್ಮ್ ಭರ್ತಿಮಾಡಿ", "📝 ಫಾರ್ಮ್ ಭರ್ತಿಮಾಡಿ"
        ])
        is_chat = any(w in msg_clean for w in [
            "chat", "chat instead", "💬 chat instead", 
            "चैट करें", "💬 चैट करें", 
            "చాట్ చేయి", "💬 చాట్ చేయి", 
            "அரட்டை செய்", "💬 அரட்டை செய்", 
            "ಚಾಟ್ ಮಾಡಿ", "💬 ಚಾಟ್ ಮಾಡಿ"
        ])
        
        if is_form:
            update_profile({"onboarding_step": "form_awaiting_submission"})
            state["reply"] = trans.get("form_choice_prompt")
            state["show_form_choice"] = True
            state["onboarding_step"] = "form_awaiting_submission"
            state["chips"] = [trans.get("chat_instead_chip", "💬 Chat Instead")]
        elif is_chat:
            update_profile({"onboarding_step": "state"})
            state["reply"] = trans.get("chat_choice_prompt")
            state["onboarding_step"] = "state"
            state["chips"] = trans.get("states")
        else:
            state["reply"] = trans.get("form_chat_intro")
            state["chips"] = [trans.get("fill_form_chip", "📝 Fill Form"), trans.get("chat_instead_chip", "💬 Chat Instead")]
        return state

    # STEP 3.5 – Form Awaiting Submission (fallback if user types chat instead)
    if current_step == "form_awaiting_submission":
        msg_clean = message.lower().strip()
        is_chat = any(w in msg_clean for w in [
            "chat", "chat instead", "💬 chat instead", 
            "चैट करें", "💬 चैट करें", 
            "చాట్ చేయి", "💬 చాట్ చేయి", 
            "அரட்டை செய்", "💬 அரட்டை செய்", 
            "ಚಾಟ್ ಮಾಡಿ", "💬 ಚಾಟ್ ಮಾಡಿ"
        ])
        if is_chat:
            update_profile({"onboarding_step": "state"})
            state["reply"] = trans.get("chat_choice_prompt")
            state["onboarding_step"] = "state"
            state["chips"] = trans.get("states")
        else:
            if msg_clean == "form submitted":
                # Triggered when form is successfully submitted in frontend
                update_profile({"onboarding_step": "confirmation", "confirmation_step": "awaiting_confirmation"})
                user_doc = sync_users_collection.find_one({"session_id": session_id}) or {}
                state["onboarding_step"] = "confirmation"
                state["confirmation_step"] = "awaiting_confirmation"
                summary = trans.get("confirm_header", "Please confirm your details:\\n\\n") + generate_profile_summary(user_doc)
                prompt = trans.get("confirm_question", "Is this information correct? (Yes/No)")
                state["reply"] = f"{summary}|||{prompt}"
                state["chips"] = [trans.get("yes", "Yes"), trans.get("no", "No")]
            else:
                state["reply"] = trans.get("form_choice_fallback")
                state["chips"] = [trans.get("chat_instead_chip", "💬 Chat Instead")]
        return state

    # Subsequent fields order
    fields_order = [
        "state",
        "occupation",
        "caste_category",
        "gender",
        "age",
        "income_bracket",
        "land_size",
        "email",
    ]
    
    questions = {
        "state": trans.get("state_q"),
        "occupation": trans.get("occupation_q"),
        "caste_category": trans.get("caste_category_q"),
        "gender": trans.get("gender_q"),
        "age": trans.get("age_q"),
        "income_bracket": trans.get("income_bracket_q"),
        "land_size": trans.get("land_size_q"),
        "email": trans.get("email_q"),
    }
    
    field_chips = {
        "state": trans.get("states"),
        "occupation": trans.get("occupations"),
        "caste_category": trans.get("castes"),
        "gender": trans.get("genders"),
        "age": ["18-25", "26-35", "36-50", "50+"],
        "income_bracket": trans.get("incomes"),
        "land_size": trans.get("lands"),
        "email": [trans.get("skip_email_chip", "Skip Email")],
    }

    if current_step in fields_order:
        val = message.strip()
        
        # Validation
        if current_step == "age":
            nums = re.findall(r'\d+', val)
            if not nums or int(nums[0]) < 1 or int(nums[0]) > 120:
                state["reply"] = trans.get("invalid_age", "Please enter a valid age (between 1 and 120).")
                state["chips"] = field_chips["age"]
                return state
            val = nums[0]
            
        elif current_step == "land_size":
            nums = re.findall(r'\d+\.?\d*', val)
            if not nums or float(nums[0]) < 0:
                state["reply"] = trans.get("invalid_land", "Please enter a valid land size in acres (e.g. 0 or 2.5).")
                state["chips"] = field_chips["land_size"]
                return state
            val = nums[0]
            
        elif current_step == "email":
            if val.lower() in ["skip", "skip email", "no email"]:
                val = ""
            elif "@" not in val or "." not in val:
                state["reply"] = trans.get("invalid_email", "Please enter a valid email address or type 'skip' to skip.")
                state["chips"] = field_chips["email"]
                return state
        
        # Normalize state/occupation/etc. to English before saving to DB
        normalized_val = normalize_to_english(current_step, val, lang)
        
        # Save to DB
        update_profile({current_step: normalized_val})
        user_doc[current_step] = normalized_val
        
        # Go to next field
        idx = fields_order.index(current_step)
        if idx + 1 < len(fields_order):
            next_field = fields_order[idx + 1]
            update_profile({"onboarding_step": next_field})
            state["onboarding_step"] = next_field
            state["reply"] = questions[next_field]
            state["chips"] = field_chips[next_field]
        else:
            update_profile({"onboarding_step": "confirmation", "confirmation_step": "awaiting_confirmation"})
            state["onboarding_step"] = "confirmation"
            state["confirmation_step"] = "awaiting_confirmation"
            summary = trans.get("confirm_header", "Please confirm your details:\\n\\n") + generate_profile_summary(user_doc)
            prompt = trans.get("confirm_question", "Is this information correct? (Yes/No)")
            state["reply"] = f"{summary}|||{prompt}"
            state["chips"] = [trans.get("yes", "Yes"), trans.get("no", "No")]
        return state

    # Handle confirmation and editing
    if current_step == "confirmation":
        conf_step = state.get("confirmation_step") or user_doc.get("confirmation_step")
        msg_clean = message.lower().strip()
        
        yes_words = ["yes", "y", "correct", "confirm", "yeah", "yes continue", "✅ yes, still correct", "yes, still correct", trans.get("yes", "Yes").lower().strip(), "అవును", "हाँ", "ஆம்", "ಹೌದು"]
        no_words = ["no", "n", "edit", "change", "edit details", "✏️ no, update details", "no, update details", trans.get("no", "No").lower().strip(), "కాదు", "नहीं", "இல்லை", "ಅಲ್ಲ"]

        if conf_step == "awaiting_confirmation":
            if any(w == msg_clean for w in yes_words) or any(w in msg_clean for w in ["yes, still correct", "✅"]):
                update_profile({"onboarding_step": "complete", "confirmation_step": None, "editing_field": None})
                state["onboarding_step"] = "complete"
                state["confirmation_step"] = None
                state["editing_field"] = None
                
                # Check if returning user navigating from login
                if user_doc.get("is_returning"):
                    state["reply"] = "Great — let me check for any schemes matching your profile..."
                
                return handle_scheme_query(state)
            elif any(w == msg_clean for w in no_words) or any(w in msg_clean for w in ["update details", "✏️"]):
                update_profile({"onboarding_step": "form_chat_choice", "confirmation_step": None})
                state["onboarding_step"] = "form_chat_choice"
                state["reply"] = trans.get("form_chat_intro")
                state["chips"] = [trans.get("fill_form_chip", "📝 Fill Form"), trans.get("chat_instead_chip", "💬 Chat Instead")]
                return state
            elif msg_clean == "form submitted":
                summary = "Here are the details you provided:\n\n" + generate_profile_summary(user_doc)
                prompt = trans.get("correct_prompt", "Please confirm if your details are correct. Answer 'Yes' or 'No'.")
                state["reply"] = f"{summary}|||{prompt}"
                state["chips"] = [trans.get("yes", "Yes"), trans.get("no", "No")]
                return state
            else:
                state["reply"] = trans.get("correct_prompt", "Please confirm if your details are correct. Answer 'Yes' or 'No'.")
                state["chips"] = [trans.get("yes", "Yes"), trans.get("no", "No")]
                return state
                
        elif conf_step == "selecting_field":
            field_map = {
                # English
                "name": "name", "state": "state", "occupation": "occupation",
                "caste category": "caste_category", "caste": "caste_category", "category": "caste_category",
                "gender": "gender", "age": "age", "income bracket": "income_bracket", "income": "income_bracket",
                "land size": "land_size", "land": "land_size", "email": "email",
                "language": "language_preference", "language preference": "language_preference",
                # Telugu
                "పేరు": "name", "రాష్ట్రం": "state", "వృత్తి": "occupation", "కుల వర్గం": "caste_category",
                "లింగం": "gender", "వయస్సు": "age", "ఆదాయ పరిమితి": "income_bracket", "భూమి పరిమాణం": "land_size", "ఇమెయిల్": "email", "భాష": "language_preference",
                # Hindi
                "नाम": "name", "राज्य": "state", "व्यवसाय": "occupation", "जाति श्रेणी": "caste_category",
                "लिंग": "gender", "उम्र": "age", "आय श्रेणी": "income_bracket", "भूमि का आकार": "land_size", "ईमेल": "email", "भाषा": "language_preference",
                # Tamil
                "பெயர்": "name", "மாநிலம்": "state", "தொழில்": "occupation", "சாதிப் பிரிவு": "caste_category",
                "பாலினம்": "gender", "வயது": "age", "வருமானப் பிரிவு": "income_bracket", "நில அளவு": "land_size", "மின்னஞ்சல்": "email", "மொழி": "language_preference",
                # Kannada
                "ಹೆಸರು": "name", "ರಾಜ್ಯ": "state", "ಉದ್ಯೋಗ": "occupation", "ಜಾತಿ ವರ್ಗ": "caste_category",
                "ಲಿಂಗ": "gender", "ವಯಸ್ಸು": "age", "ಆದಾಯ ಶ್ರೇಣಿ": "income_bracket", "ಭೂಮಿಯ ಗಾತ್ರ": "land_size", "ಇಮೇಲ್": "email", "ಭಾಷೆ": "language_preference"
            }
            field_to_edit = field_map.get(msg_clean)
            if not field_to_edit:
                state["reply"] = trans.get("edit_prompt", "Please select one of the fields to edit.")
                
                # Dynamic edit chips
                edit_chips = list(trans.get("edit_fields", ["Name", "State", "Occupation", "Caste Category", "Gender", "Age", "Income Bracket", "Land Size", "Email"]))
                lang_field_word = {"en": "Language", "hi": "भाषा", "te": "భాష", "ta": "மொழி", "kn": "ಭಾಷೆ"}.get(lang, "Language")
                if lang_field_word not in edit_chips:
                    edit_chips.append(lang_field_word)
                state["chips"] = edit_chips
                return state
            
            update_profile({"editing_field": field_to_edit, "confirmation_step": "editing_value"})
            state["editing_field"] = field_to_edit
            state["confirmation_step"] = "editing_value"
            
            field_labels_translated = {
                "name": {"en": "Name", "hi": "नाम", "te": "పేరు", "ta": "பெயர்", "kn": "ಹೆಸರು"},
                "state": {"en": "State", "hi": "राज्य", "te": "రాష్ట్రం", "ta": "மாநிலம்", "kn": "ರಾಜ್ಯ"},
                "occupation": {"en": "Occupation", "hi": "व्यवसाय", "te": "వృత్తి", "ta": "தொழில்", "kn": "ಉದ್ಯೋಗ"},
                "caste_category": {"en": "Caste Category", "hi": "जाति श्रेणी", "te": "కుల వర్గం", "ta": "சாதிப் பிரிவு", "kn": "ಜಾತಿ ವರ್ಗ"},
                "gender": {"en": "Gender", "hi": "लिंग", "te": "లింగం", "ta": "பாலினம்", "kn": "ಲಿಂಗ"},
                "age": {"en": "Age", "hi": "उम्र", "te": "వయస్సు", "ta": "வயது", "kn": "ವಯಸ್ಸು"},
                "income_bracket": {"en": "Annual Income", "hi": "वार्षिक आय", "te": "వార్షిక ఆదాయం", "ta": "ஆண்டு வருமானம்", "kn": "ವಾರ್ಷಿಕ ಆದಾಯ"},
                "land_size": {"en": "Land Size (acres)", "hi": "भूमि का आकार", "te": "భూమి పరిమాణం", "ta": "நில அளவு", "kn": "ಭೂಮಿಯ ಗಾತ್ರ"},
                "email": {"en": "Email", "hi": "ईमेल", "te": "ఇమెయిల్", "ta": "மின்னஞ்சல்", "kn": "ಇಮೇಲ್"},
                "language_preference": {"en": "Language", "hi": "भाषा", "te": "భాష", "ta": "மொழி", "kn": "ಭಾಷೆ"}
            }
            
            lbl = field_labels_translated[field_to_edit].get(lang, field_labels_translated[field_to_edit]["en"])
            state["reply"] = f"{trans.get('edit_new_val', 'Please enter your new')} {lbl}:"
            
            if field_to_edit == "language_preference":
                state["chips"] = ["English", "हिंदी", "తెలుగు", "தமிழ்", "ಕನ್ನಡ"]
            else:
                state["chips"] = field_chips.get(field_to_edit, [])
            return state
            
        elif conf_step == "editing_value":
            field_to_edit = state.get("editing_field") or user_doc.get("editing_field")
            if not field_to_edit:
                update_profile({"confirmation_step": "awaiting_confirmation"})
                state["confirmation_step"] = "awaiting_confirmation"
                return state
            
            val = message.strip()
            # Validation for edit
            if field_to_edit == "age":
                nums = re.findall(r'\d+', val)
                if not nums or int(nums[0]) < 1 or int(nums[0]) > 120:
                    state["reply"] = trans.get("invalid_age", "Please enter a valid age.")
                    state["chips"] = field_chips["age"]
                    return state
                val = nums[0]
            elif field_to_edit == "land_size":
                nums = re.findall(r'\d+\.?\d*', val)
                if not nums or float(nums[0]) < 0:
                    state["reply"] = trans.get("invalid_land", "Please enter a valid land size.")
                    state["chips"] = field_chips["land_size"]
                    return state
                val = nums[0]
            elif field_to_edit == "email":
                if val.lower() in ["skip", "skip email", "no email"]:
                    val = ""
                elif "@" not in val or "." not in val:
                    state["reply"] = trans.get("invalid_email", "Please enter a valid email.")
                    state["chips"] = field_chips["email"]
                    return state
            
            if field_to_edit == "language_preference":
                val = normalize_lang_code(val)
                # Reload translations for the new language
                lang = val
                trans = get_trans(lang)
            else:
                val = normalize_to_english(field_to_edit, val, lang)
            
            update_profile({field_to_edit: val, "confirmation_step": "awaiting_confirmation", "editing_field": None})
            user_doc = sync_users_collection.find_one({"session_id": session_id}) or {}
            
            summary = trans.get("confirm_header", "Please confirm your details:\\n\\n") + generate_profile_summary(user_doc)
            prompt = trans.get("confirm_question", "Is this information correct? (Yes/No)")
            state["reply"] = f"{summary}|||{prompt}"
            state["chips"] = [trans.get("yes", "Yes"), trans.get("no", "No")]
            state["confirmation_step"] = "awaiting_confirmation"
            state["editing_field"] = None
            return state

    state["reply"] = "Could you provide more details?"
    return state

    state["reply"] = "Could you provide more details?"
    return state


def get_retrieval_context(message: str, user_profile: dict) -> tuple:
    db_context = []
    # Search database for scheme name keyword match
    words = [w for w in re.split(r'\W+', message) if len(w) > 3]
    if words:
        regex_queries = [{"name": {"$regex": w, "$options": "i"}} for w in words]
        mongo_schemes = list(sync_schemes_collection.find({"$and": [{"verified": True}, {"$or": regex_queries}]}).limit(3))
        for s in mongo_schemes:
            db_context.append(
                f"Scheme Name: {s.get('name')}\n"
                f"Description: {s.get('description')}\n"
                f"Eligibility: {s.get('eligibility_rules')}\n"
                f"Documents: {s.get('required_documents')}\n"
                f"Apply Link: {s.get('apply_link')}\n"
                f"Deadline: {s.get('deadline')}"
            )
            
    # Live RAG / Cached ChromaDB fallback
    from rag.smart_retriever import smart_retrieve
    user_state = user_profile.get("state")
    rag_results, source_type = smart_retrieve(message, user_state)
    
    rag_context = []
    if rag_results:
        for idx, doc in enumerate(rag_results):
            rag_context.append(f"[RAG Source {idx+1} ({source_type})]: {doc}")
            
    context_str = ""
    if db_context:
        context_str += "--- MongoDB Schemes ---\n" + "\n\n".join(db_context) + "\n\n"
    if rag_context:
        context_str += "--- RAG retrieved details ---\n" + "\n\n".join(rag_context) + "\n\n"
        
    effective_source = source_type
    if db_context:
        effective_source = "live"
        
    return context_str.strip(), effective_source


def rewrite_query_with_context(message: str, history: list) -> str:
    if not history:
        return message
    history_str = "\n".join([f"User: {h.get('user_message', '')}\nBot: {h.get('bot_reply', '')}" for h in history])
    prompt = (
        "Given the following conversation history and a follow-up user query, rephrase the follow-up query to be a standalone query that can be used to search for information in a database. "
        "If the follow-up query is already standalone or clear, return it exactly as is. "
        "Do NOT answer the query, ONLY return the standalone query string."
    )
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": f"History:\n{history_str}\n\nFollow-up: {message}"}
    ]
    rewritten = safe_groq_chat(messages, temperature=0.0)
    return rewritten.strip() if rewritten else message

def call_groq_faq(message: str, user_profile: dict, context: str, history: list = None) -> Dict[str, Any]:
    profile_summary = f"Name: {user_profile.get('name')}, Language: {user_profile.get('language_preference')}, State: {user_profile.get('state')}, Occupation: {user_profile.get('occupation')}, Category: {user_profile.get('caste_category')}, Gender: {user_profile.get('gender')}, Age: {user_profile.get('age')}, Income: {user_profile.get('income_bracket')}, Land: {user_profile.get('land_size')} acres"
    
    lang_code = user_profile.get("language_preference", "en")
    lang_names = {
        "en": "English",
        "hi": "Hindi (हिंदी)",
        "te": "Telugu (తెలుగు)",
        "ta": "Tamil (தமிழ்)",
        "kn": "Kannada (ಕನ್ನಡ)"
    }
    target_lang_name = lang_names.get(lang_code, "English")

    history_str = ""
    if history:
        history_str = "Chat History:\n" + "\n".join([f"User: {h.get('user_message', '')}\nBot: {h.get('bot_reply', '')}" for h in history]) + "\n\n"

    system_prompt = (
        "You are WelfareBot, an empathetic and professional welfare assistant helping Indian citizens.\n"
        f"User Profile: {profile_summary}\n\n"
        f"{history_str}"
        f"Context from schemes database & RAG:\n{context}\n\n"
        "Answer the user's query accurately using the database/RAG context or your general knowledge if the database does not contain it (e.g. general questions like PM/CM names, greetings, help queries).\n\n"
        "Return your response in JSON format. Do NOT wrap it in ```json blocks. Return ONLY a valid JSON object with these keys:\n"
        f"1. 'reply': a detailed markdown-formatted response string in the user's language preference. "
        f"CRITICAL RULE: The user's preferred language is {target_lang_name}. You MUST write the ENTIRE 'reply' STRICTLY in {target_lang_name} ONLY. "
        f"Even if the user's input message is written in English, Hindi, or any other language, you MUST ignore the language they typed in and force your reply to be in {target_lang_name}. This is an absolute requirement.\n"
        f"2. 'chips': a list of 2-3 contextual suggestion chips (strings) for the user's next logical action (e.g., 'Apply Now' or 'Apply Offline'). The chips MUST also be strictly translated into {target_lang_name}.\n"
        "3. 'apply_link': the application URL string if the user asked about a specific scheme and a link is available in the context, else empty string.\n"
        "4. 'show_apply_button': boolean (true/false). Set this to true ONLY if the user explicitly indicated they want to apply now or click the apply button.\n\n"
        f"CRITICAL RULE: The user is a resident of {user_profile.get('state')}. NEVER recommend, discuss, or mention schemes from other specific states. Only suggest Central schemes or schemes explicitly from {user_profile.get('state')}. If the context contains a scheme from another state, IGNORE IT entirely.\n"
        "Important Rules:\n"
        "- Do NOT include 'Start Over' in the chips array (it is automatically appended by the backend).\n"
        "- If the user asks about a specific scheme, your reply MUST be a structured, detailed summary of the scheme based on context. Additionally, you MUST generate at least 4 contextual chips such as 'Apply Now', 'Eligibility Criteria', 'Required Documents', and 'Find Nearest Center'.\n"
        "- If the user asks about applying, ALWAYS offer 'Apply Offline' or 'Find Nearest Center' as one of the chips.\n"
        "- If the user chooses to apply offline or asks for physical centers, first ask them for their specific location/district if it's not clear. If their location is known, generate a realistic-looking nearby government office address (e.g., 'MRO Office, [Location]', 'Panchayat Office, [Location]') and provide it in the reply.\n"
        "- If a scheme application link is available in the context and relevant to the user query, set 'apply_link' to that URL and include 'Apply Now' in the chips."
    )
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": message}
    ]
    
    response_text = safe_groq_chat(messages, temperature=0.5)
    
    try:
        cleaned = response_text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
        
        parsed = json.loads(cleaned)
        return {
            "reply": parsed.get("reply", "I couldn't generate a reply."),
            "chips": parsed.get("chips", []),
            "apply_link": parsed.get("apply_link", ""),
            "show_apply_button": parsed.get("show_apply_button", False)
        }
    except Exception as e:
        logger.error(f"Failed to parse Groq JSON response: {e}. Raw response: {response_text}")
        return {
            "reply": response_text or "I'm sorry, I encountered an error processing that.",
            "chips": ["Find My Schemes"],
            "apply_link": "",
            "show_apply_button": False
        }


def handle_faq(state: Dict[str, Any]) -> Dict[str, Any]:
    """Answer generic and scheme questions via Groq."""
    user_doc = state.get("user_profile") or {}
    session_id = state["session_id"]
    original_message = state["message"].strip()
    history = state.get("history") or []
    
    message = rewrite_query_with_context(original_message, history)
    logger.info(f"Rewrote query: '{original_message}' -> '{message}'")
    
    # Reload profile to be safe
    user_doc = sync_users_collection.find_one({"session_id": session_id}) or {}
    
    # Gather context using rewritten query
    context, source_type = get_retrieval_context(message, user_doc)
    
    # Call Groq with original message (to answer naturally) but providing history
    res = call_groq_faq(original_message, user_doc, context, history)
    
    state["reply"] = res["reply"]
    state["chips"] = res["chips"]
    if res["apply_link"]:
        state["apply_link"] = res["apply_link"]
        
    if source_type == "live":
        state["confidence_score"] = 95
    elif source_type == "cached":
        state["confidence_score"] = 85
    else:
        state["confidence_score"] = 70
        
    return state


def handle_scheme_query(state: Dict[str, Any]) -> Dict[str, Any]:
    """Return matching schemes based on the stored user profile."""
    session_id = state["session_id"]
    user_doc = sync_users_collection.find_one({"session_id": session_id}) or {}
    
    lang = user_doc.get("language_preference", "en")
    trans = get_trans(lang)
    
    try:
        from agent.eligibility import match_schemes
        schemes = match_schemes(user_doc, sync_schemes_collection)
        logger.info(f"DEBUG handle_scheme_query: Found {len(schemes)} schemes")
        if schemes:
            show_more = state.get("show_more_schemes", False)
            if show_more:
                # Show schemes 4-6 if available, or just up to 10
                top_schemes = schemes[3:6] if len(schemes) > 3 else schemes[:3]
            else:
                top_schemes = schemes[:3]
                
            scheme_chips = [s['name'] for s in top_schemes]
            if len(schemes) > (6 if show_more else 3):
                more_word = {"en": "More Schemes", "hi": "और योजनाएं", "te": "మరిన్ని పథకాలు", "ta": "மேலும் திட்டங்கள்", "kn": "ಹೆಚ್ಚಿನ ಯೋಜನೆಗಳು"}.get(lang, "More Schemes")
                scheme_chips.append(more_word)
                
            state["chips"] = scheme_chips
            state["schemes"] = schemes
            
            def format_eligibility(rules):
                if not isinstance(rules, dict):
                    try:
                        import ast
                        rules = ast.literal_eval(str(rules))
                    except:
                        return str(rules)
                if not isinstance(rules, dict):
                    return str(rules)
                out = []
                if rules.get("state") and rules["state"] != "all": out.append(f"State: {rules['state']}")
                if rules.get("caste_category") and rules["caste_category"] != "all": out.append(f"Category: {rules['caste_category']}")
                if rules.get("gender") and rules["gender"] != "all": out.append(f"Gender: {rules['gender']}")
                if rules.get("min_age", 0) > 0: out.append(f"Min Age: {rules['min_age']}")
                if rules.get("max_age", 100) < 100: out.append(f"Max Age: {rules['max_age']}")
                if rules.get("max_income", 10000000) < 10000000: out.append(f"Max Income: ₹{rules['max_income']}")
                return ", ".join(out) if out else "Available to all citizens"

            details = "\n\n".join([f"🎯 **{s['name']}**\n{s.get('description', '')}\n*Eligibility*: {format_eligibility(s.get('eligibility_rules', {}))}" for s in top_schemes])
            
            if show_more:
                intro = {"en": "Here are some more schemes for you:", "hi": "यहाँ आपके लिए कुछ और योजनाएँ हैं:", "te": "మీ కోసం ఇక్కడ మరికొన్ని పథకాలు ఉన్నాయి:", "ta": "உங்களுக்கான மேலும் சில திட்டங்கள் இதோ:", "kn": "ನಿಮಗಾಗಿ ಇನ್ನಷ್ಟು ಯೋಜನೆಗಳು ಇಲ್ಲಿವೆ:"}.get(lang, "Here are some more schemes for you:")
            else:
                intro = trans.get("found_matches", "I found {count} schemes that match your profile!").format(count=len(schemes))
            
            if lang == "en":
                state["reply"] = f"{intro}\n\n{details}"
            else:
                lang_names = {"hi": "Hindi", "te": "Telugu", "ta": "Tamil", "kn": "Kannada"}
                prompt = f"Translate the following welfare scheme details into {lang_names.get(lang, 'the requested language')}. Keep the markdown formatting (like bold and bullet points):\n\n{intro}\n\n{details}"
                translated = safe_groq_chat([{"role": "user", "content": prompt}], temperature=0.3)
                if translated:
                    state["reply"] = translated
                else:
                    state["reply"] = f"{intro}\n\n{details}"
        else:
            state["reply"] = trans.get("no_match", "No exact matches found right now. Check back later for new schemes!")
            state["schemes"] = []
            state["chips"] = []
    except Exception as e:
        logger.error(f"Scheme query error: {e}")
        state["reply"] = trans.get("error_fetching", "I'm having trouble fetching schemes right now. Please try again later.")
        state["schemes"] = []
        state["chips"] = []
    
    state["onboarding_step"] = "complete"
    state["intent"] = "scheme_query"
    state["confidence_score"] = 100
    return state

def handle_reminder(state: Dict[str, Any]) -> Dict[str, Any]:
    """Parse and schedule a reminder."""
    session_id = state["session_id"]
    message = state["message"].strip()
    
    # We use Groq to parse the reminder details
    system_prompt = (
        "Extract the reminder topic and time from the user's message.\n"
        "Return a JSON object with 'topic' (string) and 'time' (string) describing when they want to be reminded.\n"
        "If the time is unclear, default to 'tomorrow'.\n"
        "Do NOT return markdown blocks, just the JSON."
    )
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": message}
    ]
    
    response_text = safe_groq_chat(messages, temperature=0.2)
    
    topic = "your scheme application"
    time = "soon"
    try:
        cleaned = response_text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        parsed = json.loads(cleaned.strip())
        topic = parsed.get("topic", topic)
        time = parsed.get("time", time)
    except Exception as e:
        logger.error(f"Failed to parse reminder details: {e}")
        
    # Save to MongoDB
    if sync_reminders_collection is not None:
        sync_reminders_collection.insert_one({
            "session_id": session_id,
            "topic": topic,
            "time_str": time,
            "status": "pending",
            "created_at": datetime.utcnow()
        })
    
    state["reply"] = f"✅ I've scheduled a reminder for you about '{topic}' for {time}. I will remind you when you next log in around that time!"
    state["chips"] = ["Find My Schemes", "Update Profile"]
    state["confidence_score"] = 100
    return state