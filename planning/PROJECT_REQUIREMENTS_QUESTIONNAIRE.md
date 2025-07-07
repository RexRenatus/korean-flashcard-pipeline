# Project Requirements Questionnaire

**Last Updated**: 2025-01-07

## Purpose

This questionnaire gathers detailed requirements for the Korean Language Flashcard Pipeline to ensure optimal system design and implementation decisions.

## 🎯 Project Requirements & Constraints

### 1. Volume & Performance

Please provide estimates for:
- **Batch Size**: How many vocabulary items do you expect to process per batch?
    - **I WANT EACH BATCH TO ATLEAST BE ABLE TO PROCESS 500 WORDS**

- **Daily Volume**: Expected number of items processed per day?
    - **I DONT EXPECT TO PROCESS THAT MANY, ONLY WHEN I AM RUNNING OUT OF FLASHCARDS AND NEED MORE TO BE MADE. BUT I WOULD STILL LIKE TO BE ABLE TO PROCESS AS MANY CARDS AS POSSIBLE, AND AS FAST AS POSSIBLE**

- **Monthly Volume**: Expected number of items processed per month?
    - **SAME AS ABOVE, NO GOAL FOR MASS PROCESSING AS OF YET**

- **Performance Requirements**: 
  - What's an acceptable processing time per item?
    - **AS FAST AS POSSIBLE WHILE REMAINING WITHIN THE LIMITS OF OPENROUTER API LIMITS**

  - Do you need real-time processing or is batch processing acceptable?
   - **TELL ME WHICH OPTION IS BETTER, THAN WE CAN MAKE THAT DECISION**

  - Any specific latency requirements?
    - **NO NOT RIGHT NOW**

### 2. OpenRouter API Specifics

- **API Access**: 
  - Do you already have an OpenRouter API key?
    **YES REVIEW OUR @.env FILE**

  - What's your rate limit tier? (requests per minute/hour)
    **I DONT KNOW**


- **Budget Constraints**:
  - What's your monthly token budget?
    - **N/A**

  - Cost per 1M tokens expectations?
  - **N/A**

- **Model Selection**:
  - Should we optimize for cost or quality?
    - **LETS FOCUS ON BOTH, THATS WHY I WANT TO IMPLEMENT A CACHEING MECHANISM WHICH STORE CALLS BEFORE PROCESSING TO ENSURE WE STILL HAVE THE ORIGNAL OUTPUT IN THE FUTURE**

  - Use cheaper models for Stage 1 (semantic analysis) vs Claude Sonnet 4 for everything?
    - **WE MUST! ALWAYS USE CLAUDE SONNET 4 FOR EVERYTHING**

  - Any specific model preferences?
    - **REFER TO ABOVE**

### 3. Flashcard Requirements

- **Card Types**:
  - Besides Recognition and Production cards, do you need other types?
    - **NO NOT AT THE MOMENT**

  - Cloze deletion cards?
    - **N/A**

  - Audio cards?
    - **N/A**

  - Writing practice cards?
    - **N/A**
  
- **Card Fields**: What specific fields should each flashcard contain?
  - Front/Back only?

  ### Example of output for the nuance creator
        - {
  "term_number": 1,
  "term": "남성[nam.sʌŋ]",
  "ipa": "[nam.sʌŋ]",
  "pos": "noun",
  "primary_meaning": "adult male person; man",
  "other_meanings": "masculine gender (grammatical); masculinity (abstract concept)",
  "metaphor": "A sturdy oak tree standing tall in a forest clearing",
  "metaphor_noun": "oak tree",
  "metaphor_action": "stands tall",
  "suggested_location": "forest clearing",
  "anchor_object": "oak tree",
  "anchor_sensory": "rough bark texture under fingertips",
  "explanation": "The oak tree represents traditional masculine strength and presence, standing prominently like the social role of adult males",
  "usage_context": null,
  "comparison": {
    "vs": "남자[nam.dʒa]",
    "nuance": "남성 is formal/clinical (adult male); 남자 is casual everyday term (boy/man/guy)"
  },
  "homonyms": [
    {
      "hanja": "男性",
      "reading": "남성",
      "meaning": "male gender/masculinity",
      "differentiator": "same word - hanja shows meaning components: 男 (male) + 性 (nature/gender)"
    }
  ],
  "korean_keywords": ["남성", "남자", "여성", "성별"]
          }


  ### Example of output for the nuance flashcard creator (IN TSV FORMAT)
  position	term	term_number	tab_name	primer	front	back	tags	honorific_level
1	남성[nam.sʌŋ]	1	Scene	You enter your clean, pleasant-smelling memory room. 1. Walk to the cabinet labeled 'KOREAN'. 2. Open the drawer labeled 'TERMS'. 3. Pull out the binder marked 'NOUN'. 4. Flip to the tab for 'Term #1: 남성[nam.sʌŋ]' and prepare to step through the portal.	Stepping through another portal, you enter the forest clearing. What single architectural feature demands your full attention?	A sturdy oak tree stands tall at the center, its broad trunk radiating ancient strength while rough bark catches golden sunlight. This towering presence perfectly captures how 남성[nam.sʌŋ] embodies adult male person—not just any man, but the formal, clinical designation used in medical charts and government forms. The tree's solid verticality mirrors the term's authoritative precision in distinguishing masculine gender both grammatically and as an abstract concept.	term:남성,pos:noun,card:Scene,concept:metaphor,metaphor:oak_tree	
2	남성[nam.sʌŋ]	1	Usage-Comparison	You enter your clean, pleasant-smelling memory room. 1. Walk to the cabinet labeled 'KOREAN'. 2. Open the drawer labeled 'TERMS'. 3. Pull out the binder marked 'NOUN'. 4. Flip to the tab for 'Term #1: 남성[nam.sʌŋ]' and prepare to step through the portal.	The oak tree from the forest clearing pulses with meaning as you explore how 남성[nam.sʌŋ] works in practice. How does it differ from 남자[nam.dʒa]?	Hospital marble echoes as staff announce "남성[nam.sʌŋ] 화장실[hwa.dʒaŋ.sil]"—the formal precision matching polished surfaces. Medical forms print "남성[nam.sʌŋ] 호르몬[ho.ɾɯ.mon]" in clinical black ink. Unlike everyday 남자[nam.dʒa] tossed around cafés and street corners, this oak-like term carries institutional weight—남성[nam.sʌŋ] is formal/clinical (adult male) while 남자[nam.dʒa] is the casual everyday term (boy/man/guy). The rough bark texture under fingertips reminds you how this distinction shapes every interaction.	term:남성,pos:noun,card:Usage-Comparison,comparison_term:남자	
3	남성[nam.sʌŋ]	1	Hanja	You enter your clean, pleasant-smelling memory room. 1. Walk to the cabinet labeled 'KOREAN'. 2. Open the drawer labeled 'TERMS'. 3. Pull out the binder marked 'NOUN'. 4. Flip to the tab for 'Term #1: 남성[nam.sʌŋ]' and prepare to step through the portal.	The oak tree from the forest clearing reveals hidden layers as you examine the Chinese characters. What ancient meanings emerge from the brushstrokes?	The hanja 男性[nam.sʌŋ] splits into two distinct components on rice paper—男[nam] (male) shows a field 田[tʰjen] above strength 力[njʌk̚], depicting traditional masculine labor, while 性[sʌŋ] (nature/gender) combines heart 心[sim] with life 生[sɛŋ]. Black ink bleeds slightly into fibrous paper as these ancient pictographs reveal how "male nature" became the formal designation for masculine gender. The musty smell of old scrolls mingles with fresh ink, grounding this clinical term in millennia of meaning.	term:남성,pos:noun,card:Hanja,hanja,character:男,character:性


  
- **Additional Features**: Do you need support for:
  - [ ] Audio pronunciation files
  - [ ] Multiple example sentences per card
  - [ ] Difficulty levels or frequency indicators
  - [ ] Grammar notes or cultural context
  - [ ] Images or visual aids
  - [ ] Synonyms/antonyms
  - [ ] Related vocabulary links

### 4. Input/Output Formats

- **Input CSV Format**:
  - Exact column names? (e.g., "Korean", "English", "Type")
    - **REVIEW OUR FILE @10_HSK_List.csv LOCATED IN DOCS FOLDER, ONLY FOCUS ON EXTRACTING COLUMNS FOR POSITION, AND HANGUL**

  - Character encoding? (UTF-8, UTF-16?)
    - **BEST OPTION FOR KOREAN**

  - Delimiter? (comma, tab, semicolon?)
    - **ITS A CSV FILE**

  - Quote character handling?

  - Example row?
#### EXAMPLE ROW
        Position,Hangul,IPA_Pronunciation,Word_Type,TOPIK_Level,Definition,Example_Sentence,Example_Sentence_IPA,Example_Sentence_Translation,Usage_Hint,Frequency,Frequency_Number,Verified,Quality_Score,HSK_Compliance,Processed,Reasoning_Tokens,Total_Tokens,O4_Error
        1,내가,nɛ.ka,pronoun,1,I,내가 밥을 먹었어.,nɛ.ka pap̚.ɯl mʌk̚.ʌt̚.ʌ,I ate rice.,"Subject marker attached to the pronoun I, common in spoken and casual writing",1,39801,True,Accurate and meets frequency-based definition requirements.,False,True,960,1677,


- **Output TSV Format**:
  - Exact format needed? (Anki-compatible?)
    - **position	term	term_number	tab_name	primer	front	back	tags	honorific_level**

  - Required fields?
    - **WHATS ABOVE**

  - Special formatting requirements?
  - Example output row?
#### EXAMPLE ROW:
      position	term	term_number	tab_name	primer	front	back	tags	honorific_level
1	남성[nam.sʌŋ]	1	Scene	You enter your clean, pleasant-smelling memory room. 1. Walk to the cabinet labeled 'KOREAN'. 2. Open the drawer labeled 'TERMS'. 3. Pull out the binder marked 'NOUN'. 4. Flip to the tab for 'Term #1: 남성[nam.sʌŋ]' and prepare to step through the portal.	Stepping through another portal, you enter the forest clearing. What single architectural feature demands your full attention?	A sturdy oak tree stands tall at the center, its broad trunk radiating ancient strength while rough bark catches golden sunlight. This towering presence perfectly captures how 남성[nam.sʌŋ] embodies adult male person—not just any man, but the formal, clinical designation used in medical charts and government forms. The tree's solid verticality mirrors the term's authoritative precision in distinguishing masculine gender both grammatically and as an abstract concept.	term:남성,pos:noun,card:Scene,concept:metaphor,metaphor:oak_tree	
2	남성[nam.sʌŋ]	1	Usage-Comparison	You enter your clean, pleasant-smelling memory room. 1. Walk to the cabinet labeled 'KOREAN'. 2. Open the drawer labeled 'TERMS'. 3. Pull out the binder marked 'NOUN'. 4. Flip to the tab for 'Term #1: 남성[nam.sʌŋ]' and prepare to step through the portal.	The oak tree from the forest clearing pulses with meaning as you explore how 남성[nam.sʌŋ] works in practice. How does it differ from 남자[nam.dʒa]?	Hospital marble echoes as staff announce "남성[nam.sʌŋ] 화장실[hwa.dʒaŋ.sil]"—the formal precision matching polished surfaces. Medical forms print "남성[nam.sʌŋ] 호르몬[ho.ɾɯ.mon]" in clinical black ink. Unlike everyday 남자[nam.dʒa] tossed around cafés and street corners, this oak-like term carries institutional weight—남성[nam.sʌŋ] is formal/clinical (adult male) while 남자[nam.dʒa] is the casual everyday term (boy/man/guy). The rough bark texture under fingertips reminds you how this distinction shapes every interaction.	term:남성,pos:noun,card:Usage-Comparison,comparison_term:남자	
3	남성[nam.sʌŋ]	1	Hanja	You enter your clean, pleasant-smelling memory room. 1. Walk to the cabinet labeled 'KOREAN'. 2. Open the drawer labeled 'TERMS'. 3. Pull out the binder marked 'NOUN'. 4. Flip to the tab for 'Term #1: 남성[nam.sʌŋ]' and prepare to step through the portal.	The oak tree from the forest clearing reveals hidden layers as you examine the Chinese characters. What ancient meanings emerge from the brushstrokes?	The hanja 男性[nam.sʌŋ] splits into two distinct components on rice paper—男[nam] (male) shows a field 田[tʰjen] above strength 力[njʌk̚], depicting traditional masculine labor, while 性[sʌŋ] (nature/gender) combines heart 心[sim] with life 生[sɛŋ]. Black ink bleeds slightly into fibrous paper as these ancient pictographs reveal how "male nature" became the formal designation for masculine gender. The musty smell of old scrolls mingles with fresh ink, grounding this clinical term in millennia of meaning.	term:남성,pos:noun,card:Hanja,hanja,character:男,character:性

- **Additional Export Formats**: Do you need:
  - [ ] JSON export
  - [ ] Excel (.xlsx) export
  - [ ] Anki package (.apkg) export
  - [ ] PDF export
  - [ ] Other: _______________

### 5. Caching & Data Persistence

- **Cache Duration**:
  - How long should we cache Stage 1 results? (semantic analysis rarely changes)
    **IT SHOULD BE CACHE AND STORED IN OUR DATABASE**

  - How long should we cache Stage 2 results? (generated flashcards)
    **IT SHOULD BE CACHE AND STORED IN OUR DATABASE**

  - Different TTL for different content types?

- **Cache Control**:
  - Should users be able to force regeneration of cached content?
    **IN ORDER TO SAVE FUNDS ON API COST, FAILED CARDS IN STAGE 2 SHOULD UTILIZE THE CACHE RESOONSE FROM STAGE 1**

  - Clear cache commands needed?
    NEED MORE INFORMATION

  - Cache statistics/reporting?
    - **THIS SHOULD BE TRACKED IN ORDER TO MAINTAIN THE HEALTH OF THE DATABASE**

- **Data Management**:
  - Do you need to track version history of generated cards?
    **IF IT WOULD BE RELEVANT**

  - Support multiple versions (e.g., different difficulty levels) of the same vocabulary item?
      **I DONT THINK THIS IS NECESSARY**

  - Backup requirements?


### 6. Error Handling & Recovery

- **Partial Failure Handling**: If API calls fail partway through a batch:
  - [ ] Save partial progress
  - [Y ] Retry failed items automatically
  - [ ] Generate a report of failed items
  - [ ] Send notifications
  - [ ] Other: **MAINTAING WITH THE USE OF A DATABASE WE WONT HAVE TO WORRY ABOVE LOSING OUR PLACE, AND CAN JUST RETRY FAILED CARD IF NEEDED**

- **Retry Strategy**:
  - Maximum retry attempts?
    **3 IF NOT ABLE TO GENERATE, OUTPUT A REPORT FOR THE USER TO KNOW WHY AND WHAT TO DO NEXT**

  - Exponential backoff preferences?
    **WHAT EVER IS NECESSARY**

  - What should happen with consistently failing items?
    **QUARANTINE FOR INSPECTION**

- **Error Reporting**:
  - Log file format preferences?
  **WHAT EVER IS NECESSARY**

  - Error notification requirements?
  **WHAT EVER IS NECESSARY**

  - Debug information needs?
  **WHAT EVER IS NECESSARY**

### 7. User Interface & Workflow

- **Target Users**: Who will use this system?
  - [Y ] Teachers
  - [Y ] Students
  - [Y ] Content creators
  - [ ] Administrators
  - [ Y] Other: TUTORS

- **Interface Preferences**:
  - [Y ] CLI only (current plan) **FOR NOW WE WILL ONLY FOCUS ON BASIC FUNCTIONALITY, MAY VISIT THE REST DOWN THE LINE**
  - [ ] Web interface later
  - [ ] REST API for integration
  - [ ] Desktop application
  - [ ] Other: _______________

- **Multi-user Support**:
  - Should it support multiple users/projects?
  **N/A**
  - Authentication requirements?
  **N/A**
  - User roles/permissions?
  **N/A**

### 8. Special Features

Do you need any of these advanced features:
- [Y ] Batch scheduling/queuing
- [N ] Progress notifications (email, webhook)
- [Y ] Quality scoring/filtering of generated cards
- [ N] A/B testing different prompts
- [ N] Custom prompt templates
- [Y ] Bulk operations UI
- [ Y] Analytics dashboard
- [ Y] Content moderation/review workflow
- [ N] Integration with spaced repetition algorithms
- [N ] Other: _______________

### 9. Integration Requirements

- **External Systems**:
  - Will this integrate with any existing systems?
  **N/A**
  - API requirements for other tools?
  **N/A**
  - Webhook endpoints needed?
  **N/A**

- **Korean Language Specifics**:
  - Romanization system preference? 
    - [ ] Revised Romanization
    - [ ] McCune-Reischauer
    - [ ] Yale
    - [ ] Other: LLM IPA GENERATED
  
  - Korean language levels to consider?
  **N/A**

- **Import Sources**: Will you import vocabulary from:
  - @10_HSK_LIST

### 10. Development Priorities

- **MVP Definition**: What constitutes the Minimum Viable Product?
  - Must-have features:
   ASSIST ME WITH THIS
  
  - Nice-to-have features:
    ASSIST ME WITH THIS

- **Development Approach**:
  - [ ] Quick prototype that works → iterate
  - [ ] Robust foundation → build features
  - [Y ] Hybrid approach

- **Timeline**:
  -**N/A**

### 11. Additional Considerations

- **Compliance/Legal**:
 **N/A**

- **Performance Metrics**: How do you measure success?
  DOES IT WORK THE WAY WE WANT IT TO WORK


- **Future Vision**:
  NO VISION YET, I AM JUST TRYING TO BUILD AND GIVE BACK

## Notes Section

**N/A**

## Next Steps

Once you've filled out this questionnaire, we can:
1. Create a detailed system architecture
2. Define API specifications
3. Design the integration approach
4. Plan the implementation phases

Please take your time to think through these questions. The more detail you provide, the better we can tailor the system to your needs.