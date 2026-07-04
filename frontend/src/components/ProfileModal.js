import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './ProfileModal.css';

const API = process.env.REACT_APP_API_URL || '';

const LANGS = ['English', 'Hindi', 'Telugu', 'Tamil', 'Kannada'];
const LANG_NAME_TO_CODE = {
  'English': 'en',
  'Hindi': 'hi',
  'Telugu': 'te',
  'Tamil': 'ta',
  'Kannada': 'kn',
  'en': 'en',
  'hi': 'hi',
  'te': 'te',
  'ta': 'ta',
  'kn': 'kn'
};
const LANG_CODE_TO_NAME = {
  'en': 'English',
  'hi': 'Hindi',
  'te': 'Telugu',
  'ta': 'Tamil',
  'kn': 'Kannada'
};

const FORM_TRANSLATIONS = {
  en: {
    title: "Find Your Schemes",
    subtitle: "Fill in your details to see matching schemes",
    name: "Full Name *",
    namePlaceholder: "e.g. Kushan Sharma",
    language: "Language *",
    state: "State / UT *",
    stateSelect: "Select state",
    occupation: "Occupation *",
    occupationSelect: "Select occupation",
    category: "Category *",
    gender: "Gender *",
    genderOptions: ["Male", "Female", "Other"],
    age: "Age *",
    agePlaceholder: "e.g. 28",
    income: "Annual Income *",
    incomeSelect: "Select range",
    land: "Land Size (acres)",
    landPlaceholder: "e.g. 5",
    email: "Email (optional)",
    emailPlaceholder: "e.g. kushan@example.com",
    cancel: "Cancel",
    submit: "Find My Schemes",
    checking: "Checking...",
    errorFill: "Please fill in: ",
    errorAge: "Enter a valid age (1-120).",
    errorConnection: "Failed to submit. Check your connection.",
    states: ['Andhra Pradesh','Arunachal Pradesh','Assam','Bihar','Chhattisgarh','Goa','Gujarat','Haryana','Himachal Pradesh','Jharkhand','Karnataka','Kerala','Madhya Pradesh','Maharashtra','Manipur','Meghalaya','Mizoram','Nagaland','Odisha','Punjab','Rajasthan','Sikkim','Tamil Nadu','Telangana','Tripura','Uttar Pradesh','Uttarakhand','West Bengal','Delhi','Jammu & Kashmir','Ladakh'],
    occupations: ['Student','Farmer','Daily Wage Worker','Self Employed','Government Employee','Private Employee','Unemployed','Homemaker','Retired','Other'],
    incomes: ['Below Rs.1 Lakh','Rs.1-2.5 Lakh','Rs.2.5-5 Lakh','Rs.5-10 Lakh','Above Rs.10 Lakh'],
    castes: ['General','OBC','SC','ST','EWS']
  },
  hi: {
    title: "अपनी योजनाएं खोजें",
    subtitle: "योग्य योजनाओं को देखने के लिए अपना विवरण भरें",
    name: "पूरा नाम *",
    namePlaceholder: "उदा. कुशन शर्मा",
    language: "भाषा *",
    state: "राज्य / केंद्र शासित प्रदेश *",
    stateSelect: "राज्य चुनें",
    occupation: "व्यवसाय *",
    occupationSelect: "व्यवसाय चुनें",
    category: "श्रेणी *",
    gender: "लिंग *",
    genderOptions: ["पुरुष", "महिला", "अन्य"],
    age: "उम्र *",
    agePlaceholder: "उदा. 28",
    income: "वार्षिक आय *",
    incomeSelect: "आय सीमा चुनें",
    land: "भूमि का आकार (एकड़)",
    landPlaceholder: "उदा. 5",
    email: "ईमेल (वैकल्पिक)",
    emailPlaceholder: "उदा. kushan@example.com",
    cancel: "रद्द करें",
    submit: "मेरी योजनाएं खोजें",
    checking: "जांच की जा रही है...",
    errorFill: "कृपया भरें: ",
    errorAge: "वैध उम्र दर्ज करें (1-120)।",
    errorConnection: "सबमिट करने में विफल। अपना कनेक्शन जांचें।",
    states: ["आंध्र प्रदेश", "अरुणाचल प्रदेश", "असम", "बिहार", "छत्तीसगढ़", "गोवा", "गुजरात", "हरियाणा", "हिमाचल प्रदेश", "झारखंड", "कर्नाटक", "केरल", "मध्य प्रदेश", "महाराष्ट्र", "मणिपुर", "मेघालय", "मिजोरम", "नागालैंड", "ओडिशा", "पंजाब", "राजस्थान", "सिक्किम", "तमिलनाडु", "तेलंगाना", "त्रिपुरा", "उत्तर प्रदेश", "उत्तराखंड", "पश्चिम बंगाल", "दिल्ली", "जम्मू और कश्मीर", "लद्दाख"],
    occupations: ["छात्र", "किसान", "दैनिक वेतन भोगी", "स्व-नियोजित", "सरकारी कर्मचारी", "निजी कर्मचारी", "बेरोजगार", "गृहणी", "सेवानिवृत्त", "अन्य"],
    incomes: ["1 लाख रुपये से कम", "1-2.5 लाख रुपये", "2.5-5 लाख रुपये", "5-10 लाख रुपये", "10 लाख रुपये से अधिक"],
    castes: ["सामान्य", "OBC", "SC", "ST", "EWS"]
  },
  te: {
    title: "మీ పథకాలను కనుగొనండి",
    subtitle: "సరిపోయే పథకాలను చూడటానికి మీ వివరాలను పూరించండి",
    name: "పూర్తి పేరు *",
    namePlaceholder: "ఉదా. కుషన్ శర్మ",
    language: "భాష *",
    state: "రాష్ట్రం / కేంద్రపాలిత ప్రాంతం *",
    stateSelect: "రాష్ట్రాన్ని ఎంచుకోండి",
    occupation: "వృత్తి *",
    occupationSelect: "వృత్తిని ఎంచుకోండి",
    category: "వర్గం *",
    gender: "లింగం *",
    genderOptions: ["పురుషుడు", "స్త్రీ", "ఇతర"],
    age: "వయస్సు *",
    agePlaceholder: "ఉదా. 28",
    income: "వార్షిక ఆదాయం *",
    incomeSelect: "పరిమితిని ఎంచుకోండి",
    land: "భూమి పరిమాణం (ఎకరాలు)",
    landPlaceholder: "ఉదా. 5",
    email: "ఇమెయిల్ (ఆప్షనల్)",
    emailPlaceholder: "ఉదా. kushan@example.com",
    cancel: "రద్దు చేయి",
    submit: "నా పథకాలను కనుగొను",
    checking: "పరిశీలిస్తోంది...",
    errorFill: "దయచేసి పూరించండి: ",
    errorAge: "సరైన వయస్సును నమోదు చేయండి (1-120).",
    errorConnection: "సమర్పించడం విఫలమైంది. మీ కనెక్షన్‌ని తనిఖీ చేయండి.",
    states: ["ఆంధ్రప్రదేశ్", "అరుణాచల్ ప్రదేశ్", "అస్సాం", "బీహార్", "ఛత్తీస్‌గఢ్", "గోవా", "గుజరాత్", "హర్యానా", "హిమాచల్ ప్రదేశ్", "ಜಾರ್ಖಂಡ್", "ಕರ್ನಾಟಕ", "కేరళ", "మధ్యప్రదేశ్", "మహారాష్ట్ర", "మణిపూర్", "మేఘాలయ", "మిజోరం", "నాగాలాండ్", "ఒడిశా", "పంజాబ్", "రాజస్థాన్", "సిక్కిం", "తమిళనాడు", "తెలంగాణ", "త్రిపుర", "ఉత్తర ప్రదేశ్", "ఉత్తరాఖండ్", "పశ్చిమ బెంగాల్", "ఢిల్లీ", "జమ్మూ & కాశ్మీర్", "లడఖ్"],
    occupations: ["విద్యార్థి", "రైతు", "రోజువారీ కూలీ", "స్వయం ఉపాధి", "ప్రభుత్వ ఉద్యోగి", "ప్రైవేట్ ఉద్యోగి", "నిరుద్యోగి", "గృహిణి", "పదవీ విరమణ పొందినవారు", "ఇతర"],
    incomes: ["1 లక్ష కంటే తక్కువ", "1-2.5 లక్షలు", "2.5-5 లక్షలు", "5-10 లక్షలు", "10 లక్షల కంటే ఎక్కువ"],
    castes: ["జనరల్", "OBC", "SC", "ST", "EWS"]
  },
  ta: {
    title: "உங்கள் திட்டங்களைக் கண்டறியவும்",
    subtitle: "பொருத்தமான திட்டங்களைக் காண உங்கள் விவரங்களை நிரப்பவும்",
    name: "முழு பெயர் *",
    namePlaceholder: "எ.கா. குஷன் சர்மா",
    language: "மொழி *",
    state: "மாநிலம் / யூனியன் பிரதேசம் *",
    stateSelect: "மாநிலத்தைத் தேர்ந்தெடுக்கவும்",
    occupation: "தொழில் *",
    occupationSelect: "தொழிலைத் தேர்ந்தெடுக்கவும்",
    category: "பிரிவு *",
    gender: "பாலினம் *",
    genderOptions: ["ஆண்", "பெண்", "இதர"],
    age: "வயது *",
    agePlaceholder: "எ.கா. 28",
    income: "ஆண்டு வருமானம் *",
    incomeSelect: "வருமானத்தைத் தேர்ந்தெடுக்கவும்",
    land: "நில அளவு (ஏக்கர்)",
    landPlaceholder: "எ.கா. 5",
    email: "மின்னஞ்சல் (விருப்பத்தேர்வு)",
    emailPlaceholder: "எ.கா. kushan@example.com",
    cancel: "ரத்துசெய்",
    submit: "எனக்கான திட்டங்களைக் காண்க",
    checking: "சரிபார்க்கிறது...",
    errorFill: "தயவுசெய்து நிரப்பவும்: ",
    errorAge: "சரியான வயதை உள்ளிடவும் (1-120).",
    errorConnection: "சமர்ப்பிக்க முடியவில்லை. இணைய இணைப்பைச் சரிபார்க்கவும்.",
    states: ["ஆந்திரப் பிரதேசம்", "அருணாச்சலப் பிரதேசம்", "அசாம்", "பீகார்", "சத்தீஸ்கர்", "கோவா", "குஜராத்", "ஹரியானா", "இமாச்சலப் பிரதேசம்", "ஜார்கண்ட்", "கர்நாடகா", "கேரளா", "மத்தியப் பிரதேசம்", "மகாராஷ்டிரா", "மணிப்பூர்", "மேகாலயா", "மிசோரம்", "நாகாலாந்து", "ஒடிசா", "பஞ்சாப்", "ராஜஸ்தான்", "சிக்கிம்", "தமிழ்நாடு", "தெலங்கானா", "திரிபுரா", "உத்தரப் பிரதேசம்", "உத்தராகண்ட்", "மேற்கு வங்காளம்", "டெல்லி", "ஜம்மு காஷ்மீர்", "லடாக்"],
    occupations: ["மாணவர்", "விவசாயி", "தினசரி கூலி", "சுயதொழில்", "அரசு ஊழியர்", "தனியார் ஊழியர்", "வேலையில்லாதவர்", "இல்லத்தரசி", "ஓய்வு பெற்றவர்", "மற்றவை"],
    incomes: ["1 லட்சத்திற்கும் குறைவாக", "1-2.5 லட்சம்", "2.5-5 லட்சம்", "5-10 லட்சம்", "10 லட்சத்திற்கும் மேல்"],
    castes: ["பொது", "OBC", "SC", "ST", "EWS"]
  },
  kn: {
    title: "ನಿಮ್ಮ ಯೋಜನೆಗಳನ್ನು ಹುಡುಕಿ",
    subtitle: "ಹೊಂದುವ ಯೋಜನೆಗಳನ್ನು ನೋಡಲು ನಿಮ್ಮ ವಿವರಗಳನ್ನು ಭರ್ತಿ ಮಾಡಿ",
    name: "ಪೂರ್ಣ ಹೆಸರು *",
    namePlaceholder: "ಉದಾ. ಕುಶನ್ ಶರ್ಮಾ",
    language: "ಭಾಷೆ *",
    state: "ರಾಜ್ಯ / ಕೇಂದ್ರಾಡಳಿತ ಪ್ರದೇಶ *",
    stateSelect: "ರಾಜ್ಯ ಆಯ್ಕೆಮಾಡಿ",
    occupation: "ಉದ್ಯೋಗ *",
    occupationSelect: "ಉದ್ಯೋಗ ಆಯ್ಕೆಮಾಡಿ",
    category: "ವರ್ಗ *",
    gender: "ಲಿಂಗ *",
    genderOptions: ["ಪುರುಷ", "ಮಹಿಳೆ", "ಇತರ"],
    age: "ವಯಸ್ಸು *",
    agePlaceholder: "ಉದಾ. 28",
    income: "ವಾರ್ಷಿಕ ಆದಾಯ *",
    incomeSelect: "ಆದಾಯ ಶ್ರೇಣಿ ಆಯ್ಕೆಮಾಡಿ",
    land: "ಭೂಮಿಯ ಗಾತ್ರ (ಎಕರೆ)",
    landPlaceholder: "ಉದಾ. 5",
    email: "ಇಮೇಲ್ (ಐಚ್ಛಿಕ)",
    emailPlaceholder: "ಉದಾ. kushan@example.com",
    cancel: "ರದ್ದುಮಾಡಿ",
    submit: "ನನ್ನ ಯೋಜನೆಗಳನ್ನು ಹುಡುಕಿ",
    checking: "ಪರಿಶೀಲಿಸಲಾಗುತ್ತಿದೆ...",
    errorFill: "ದಯವಿಟ್ಟು ಭರ್ತಿ ಮಾಡಿ: ",
    errorAge: "ಮಾನ್ಯವಾದ ವಯಸ್ಸನ್ನು ನಮೂದಿಸಿ (1-120).",
    errorConnection: "ಸಲ್ಲಿಸಲು ವಿಫಲವಾಗಿದೆ. ನಿಮ್ಮ ಸಂಪರ್ಕವನ್ನು ಪರಿಶೀಲಿಸಿ.",
    states: ["ಆಂಧ್ರ ಪ್ರದೇಶ", "ಅರುಣಾಚಲ ಪ್ರದೇಶ", "ಅಸ್ಸಾಂ", "ಬಿಹಾರ", "ಛತ್ತೀಸ್‌ಗಢ", "ಗೋವಾ", "ಗುಜರಾತ್", "ಹರಿಯಾಣ", "ಹಿಮಾಚಲ ಪ್ರದೇಶ", "ಜಾರ್ಖಂಡ್", "ಕರ್ನಾಟಕ", "ಕೇರಳ", "ಮಧ್ಯ ಪ್ರದೇಶ", "ಮಹಾರಾಷ್ಟ್ರ", "ಮಣಿಪುರ", "ಮೇಘಾಲಯ", "ಮಿಜೋರಾಂ", "ನಾಗಾಲ್ಯಾಂಡ್", "ಒಡಿಶಾ", "ಪಂಜಾಬ್", "ರಾಜಸ್ಥಾನ", "ಸಿಕ್ಕಿಂ", "ತಮಿಳುನಾಡು", "ತೆಲಂಗಾಣ", "ತ್ರಿಪುರ", "ಉತ್ತರ ಪ್ರದೇಶ", "ಉತ್ತರಾಖಂಡ", "ಪಶ್ಚಿಮ ಬಂಗಾಳ", "ದೆಹಲಿ", "ಜಮ್ಮು ಮತ್ತು ಕಾಶ್ಮೀರ", "ಲಡಾಖ್"],
    occupations: ["ವಿದ್ಯಾರ್ಥಿ", "ರೈತು", "ದಿನಗೂಲಿ ನೌಕರ", "ಸ್ವಯಂ ಉದ್ಯೋಗಿ", "ಸರ್ಕಾರಿ ನೌಕರ", "ಖಾಸಗಿ ನೌಕರ", "ನಿರುದ್ಯೋಗಿ", "ಗೃಹಿಣಿ", "ನಿವೃತ್ತರು", "ಇತರ"],
    incomes: ["1 ಲಕ್ಷಕ್ಕಿಂತ ಕಡಿಮೆ", "1-2.5 ಲಕ್ಷ", "2.5-5 ಲಕ್ಷ", "5-10 ಲಕ್ಷ", "10 ಲಕ್ಷಕ್ಕಿಂತ ಹೆಚ್ಚು"],
    castes: ["ಸಾಮಾನ್ಯ", "OBC", "SC", "ST", "EWS"]
  }
};

export default function ProfileModal({ sessionId, onClose, onSuccess }) {
  const [form, setForm] = useState({ 
    name: '', 
    language_preference: 'English', 
    state: '', 
    occupation: '', 
    caste_category: '', 
    gender: '', 
    age: '', 
    income_bracket: '', 
    land_size: '', 
    email: '' 
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const set = (k, v) => setForm(p => ({...p, [k]: v}));

  // Fetch session data on mount
  useEffect(() => {
    axios.get(`${API}/session?session_id=${sessionId}`)
      .then(res => {
        if (res.data && res.data.profile) {
          const p = res.data.profile;
          setForm(prev => ({
            ...prev,
            name: p.name || prev.name,
            language_preference: LANG_CODE_TO_NAME[p.language_preference] || p.language_preference || prev.language_preference,
            state: p.state || prev.state,
            occupation: p.occupation || prev.occupation,
            caste_category: p.caste_category || prev.caste_category,
            gender: p.gender || prev.gender,
            age: p.age || prev.age,
            income_bracket: p.income_bracket || prev.income_bracket,
            land_size: p.land_size || prev.land_size,
            email: p.email || prev.email
          }));
        }
      })
      .catch(err => console.error("Error loading session profile:", err));
  }, [sessionId]);

  const getLangCode = (langName) => {
    return LANG_NAME_TO_CODE[langName] || 'en';
  };

  const langCode = getLangCode(form.language_preference);
  const t = FORM_TRANSLATIONS[langCode] || FORM_TRANSLATIONS['en'];

  const handleSubmit = async (e) => {
    e.preventDefault(); 
    setError('');
    const req = ['name', 'state', 'occupation', 'caste_category', 'gender', 'age', 'income_bracket'];
    
    for (const f of req) { 
      if (!form[f] || !form[f].toString().trim()) { 
        setError(t.errorFill + f.replace('_', ' ')); 
        return; 
      } 
    }
    
    if (isNaN(+form.age) || +form.age < 1 || +form.age > 120) { 
      setError(t.errorAge); 
      return; 
    }

    setLoading(true);
    try {
      await axios.post(API + '/submit-profile', { 
        session_id: sessionId, 
        ...form,
        language_preference: getLangCode(form.language_preference)
      });
      if (onSuccess) onSuccess();
    } catch (err) { 
      setError(t.errorConnection); 
    } finally { 
      setLoading(false); 
    }
  };

  const Chip = ({ field, val }) => (
    <button 
      type='button' 
      className={form[field] === val ? 'sel-chip selected' : 'sel-chip'} 
      onClick={() => set(field, val)}
    >
      {val}
    </button>
  );

  return (
    <div className='modal-overlay' onClick={e => e.target === e.currentTarget && onClose()}>
      <div className='modal-box'>
        <div className='modal-header'>
          <div>
            <div className='modal-title'>{t.title}</div>
            <div className='modal-subtitle'>{t.subtitle}</div>
          </div>
          <button className='modal-close' onClick={onClose}>x</button>
        </div>
        <form className='modal-form' onSubmit={handleSubmit}>
          <div className='form-grid'>
            <div className='form-field'>
              <label className='field-label'>{t.name}</label>
              <input 
                type='text' 
                value={form.name} 
                onChange={e => set('name', e.target.value)} 
                placeholder={t.namePlaceholder} 
                autoComplete='off' 
              />
            </div>
            
            <div className='form-field full'>
              <label className='field-label'>{t.language}</label>
              <div className='chip-select'>
                {LANGS.map(l => <Chip key={l} field='language_preference' val={l} />)}
              </div>
            </div>
            
            <div className='form-field'>
              <label className='field-label'>{t.state}</label>
              <select value={form.state} onChange={e => set('state', e.target.value)}>
                <option value=''>{t.stateSelect}</option>
                {t.states.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            
            <div className='form-field'>
              <label className='field-label'>{t.occupation}</label>
              <select value={form.occupation} onChange={e => set('occupation', e.target.value)}>
                <option value=''>{t.occupationSelect}</option>
                {t.occupations.map(o => <option key={o} value={o}>{o}</option>)}
              </select>
            </div>
            
            <div className='form-field full'>
              <label className='field-label'>{t.category}</label>
              <div className='chip-select'>
                {t.castes.map(c => <Chip key={c} field='caste_category' val={c} />)}
              </div>
            </div>
            
            <div className='form-field full'>
              <label className='field-label'>{t.gender}</label>
              <div className='chip-select'>
                {t.genderOptions.map(g => <Chip key={g} field='gender' val={g} />)}
              </div>
            </div>
            
            <div className='form-field'>
              <label className='field-label'>{t.age}</label>
              <input 
                type='number' 
                value={form.age} 
                onChange={e => set('age', e.target.value)} 
                placeholder={t.agePlaceholder} 
                min='1' 
                max='120' 
                autoComplete='off' 
              />
            </div>
            
            <div className='form-field'>
              <label className='field-label'>{t.income}</label>
              <select value={form.income_bracket} onChange={e => set('income_bracket', e.target.value)}>
                <option value=''>{t.incomeSelect}</option>
                {t.incomes.map(i => <option key={i} value={i}>{i}</option>)}
              </select>
            </div>
            
            <div className='form-field'>
              <label className='field-label'>{t.land}</label>
              <input 
                type='number' 
                value={form.land_size} 
                onChange={e => set('land_size', e.target.value)} 
                placeholder={t.landPlaceholder} 
                min='0' 
                autoComplete='off' 
              />
            </div>
            
            <div className='form-field'>
              <label className='field-label'>{t.email}</label>
              <input 
                type='email' 
                value={form.email} 
                onChange={e => set('email', e.target.value)} 
                placeholder={t.emailPlaceholder} 
                autoComplete='off' 
              />
            </div>
          </div>
          
          {error && <div className='form-error'>{error}</div>}
          
          <div className='form-footer'>
            <button type='button' className='btn-secondary' onClick={onClose}>{t.cancel}</button>
            <button type='submit' className='btn-primary' disabled={loading}>
              {loading ? t.checking : t.submit}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
