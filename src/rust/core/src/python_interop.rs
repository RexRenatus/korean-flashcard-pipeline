use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use chrono::{DateTime, Utc};
use std::collections::HashMap;

use crate::models::{
    VocabularyItem, DifficultyLevel, Stage1Result, Stage2Result,
    SemanticAnalysis, FrequencyLevel, FormalityLevel,
    FlashcardContent, CardFace, CardType,
};

impl ToPyObject for DifficultyLevel {
    fn to_object(&self, py: Python<'_>) -> PyObject {
        match self {
            DifficultyLevel::Beginner => "beginner",
            DifficultyLevel::Elementary => "elementary",
            DifficultyLevel::Intermediate => "intermediate",
            DifficultyLevel::Advanced => "advanced",
            DifficultyLevel::Native => "native",
        }
        .to_object(py)
    }
}

impl FromPyObject<'_> for DifficultyLevel {
    fn extract(ob: &PyAny) -> PyResult<Self> {
        let s: String = ob.extract()?;
        match s.to_lowercase().as_str() {
            "beginner" => Ok(DifficultyLevel::Beginner),
            "elementary" => Ok(DifficultyLevel::Elementary),
            "intermediate" => Ok(DifficultyLevel::Intermediate),
            "advanced" => Ok(DifficultyLevel::Advanced),
            "native" => Ok(DifficultyLevel::Native),
            _ => Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                format!("Invalid difficulty level: {}", s),
            )),
        }
    }
}

#[pyclass]
#[derive(Clone)]
pub struct PyVocabularyItem {
    pub inner: VocabularyItem,
}

#[pymethods]
impl PyVocabularyItem {
    #[new]
    #[pyo3(signature = (korean, english, category, **kwargs))]
    fn new(
        korean: String,
        english: String,
        category: String,
        kwargs: Option<&PyDict>,
    ) -> PyResult<Self> {
        let mut item = VocabularyItem::new(korean, english, category);
        
        if let Some(dict) = kwargs {
            if let Ok(hanja) = dict.get_item("hanja") {
                if let Some(h) = hanja {
                    item.hanja = Some(h.extract()?);
                }
            }
            
            if let Ok(subcategory) = dict.get_item("subcategory") {
                if let Some(s) = subcategory {
                    item.subcategory = Some(s.extract()?);
                }
            }
            
            if let Ok(tags) = dict.get_item("tags") {
                if let Some(t) = tags {
                    item.tags = t.extract()?;
                }
            }
            
            if let Ok(difficulty) = dict.get_item("difficulty_level") {
                if let Some(d) = difficulty {
                    item.difficulty_level = d.extract()?;
                }
            }
            
            if let Ok(source) = dict.get_item("source") {
                if let Some(s) = source {
                    item.source = s.extract()?;
                }
            }
            
            if let Ok(example) = dict.get_item("example_sentence") {
                if let Some(e) = example {
                    item.example_sentence = Some(e.extract()?);
                }
            }
            
            if let Ok(notes) = dict.get_item("notes") {
                if let Some(n) = notes {
                    item.notes = Some(n.extract()?);
                }
            }
        }
        
        Ok(PyVocabularyItem { inner: item })
    }

    #[getter]
    fn korean(&self) -> &str {
        &self.inner.korean
    }

    #[getter]
    fn english(&self) -> &str {
        &self.inner.english
    }

    #[getter]
    fn category(&self) -> &str {
        &self.inner.category
    }

    #[getter]
    fn hanja(&self) -> Option<&str> {
        self.inner.hanja.as_deref()
    }

    #[getter]
    fn difficulty_level(&self) -> String {
        format!("{:?}", self.inner.difficulty_level).to_lowercase()
    }

    #[getter]
    fn tags(&self, py: Python<'_>) -> PyResult<PyObject> {
        Ok(self.inner.tags.to_object(py))
    }

    fn generate_cache_key(&self) -> String {
        self.inner.generate_cache_key()
    }

    fn to_dict(&self, py: Python<'_>) -> PyResult<PyObject> {
        let dict = PyDict::new(py);
        dict.set_item("korean", &self.inner.korean)?;
        dict.set_item("english", &self.inner.english)?;
        dict.set_item("category", &self.inner.category)?;
        
        if let Some(hanja) = &self.inner.hanja {
            dict.set_item("hanja", hanja)?;
        }
        
        if let Some(subcategory) = &self.inner.subcategory {
            dict.set_item("subcategory", subcategory)?;
        }
        
        dict.set_item("tags", &self.inner.tags)?;
        dict.set_item("difficulty_level", self.difficulty_level())?;
        dict.set_item("source", &self.inner.source)?;
        
        if let Some(example) = &self.inner.example_sentence {
            dict.set_item("example_sentence", example)?;
        }
        
        if let Some(notes) = &self.inner.notes {
            dict.set_item("notes", notes)?;
        }
        
        Ok(dict.into())
    }
}

pub fn convert_stage1_result_from_py(py_obj: &PyAny) -> PyResult<Stage1Result> {
    let dict = py_obj.downcast::<PyDict>()?;
    
    let vocabulary_id: i64 = dict.get_item("vocabulary_id")
        .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyKeyError, _>("Missing vocabulary_id"))?
        .extract()?;
    
    let request_id: String = dict.get_item("request_id")
        .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyKeyError, _>("Missing request_id"))?
        .extract()?;
    
    let cache_key: String = dict.get_item("cache_key")
        .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyKeyError, _>("Missing cache_key"))?
        .extract()?;
    
    let semantic_dict = dict.get_item("semantic_analysis")
        .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyKeyError, _>("Missing semantic_analysis"))?
        .downcast::<PyDict>()?;
    
    let semantic_analysis = SemanticAnalysis {
        primary_meaning: semantic_dict.get_item("primary_meaning")
            .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyKeyError, _>("Missing primary_meaning"))?
            .extract()?,
        alternative_meanings: semantic_dict.get_item("alternative_meanings")
            .unwrap_or(&PyList::empty(semantic_dict.py()).into())
            .extract()?,
        connotations: semantic_dict.get_item("connotations")
            .unwrap_or(&PyList::empty(semantic_dict.py()).into())
            .extract()?,
        register: semantic_dict.get_item("register")
            .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyKeyError, _>("Missing register"))?
            .extract()?,
        usage_contexts: semantic_dict.get_item("usage_contexts")
            .unwrap_or(&PyList::empty(semantic_dict.py()).into())
            .extract()?,
        cultural_notes: semantic_dict.get_item("cultural_notes")
            .and_then(|v| v.extract().ok()),
        frequency: semantic_dict.get_item("frequency")
            .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyKeyError, _>("Missing frequency"))?
            .extract::<String>()?
            .parse()
            .map_err(|_| PyErr::new::<pyo3::exceptions::PyValueError, _>("Invalid frequency"))?,
        formality: semantic_dict.get_item("formality")
            .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyKeyError, _>("Missing formality"))?
            .extract::<String>()?
            .parse()
            .map_err(|_| PyErr::new::<pyo3::exceptions::PyValueError, _>("Invalid formality"))?,
    };
    
    Ok(Stage1Result {
        vocabulary_id,
        request_id,
        cache_key,
        semantic_analysis,
        created_at: Utc::now(),
    })
}

pub fn convert_stage2_result_from_py(py_obj: &PyAny) -> PyResult<Stage2Result> {
    let dict = py_obj.downcast::<PyDict>()?;
    
    let vocabulary_id: i64 = dict.get_item("vocabulary_id")
        .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyKeyError, _>("Missing vocabulary_id"))?
        .extract()?;
    
    let stage1_cache_key: String = dict.get_item("stage1_cache_key")
        .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyKeyError, _>("Missing stage1_cache_key"))?
        .extract()?;
    
    let request_id: String = dict.get_item("request_id")
        .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyKeyError, _>("Missing request_id"))?
        .extract()?;
    
    let cache_key: String = dict.get_item("cache_key")
        .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyKeyError, _>("Missing cache_key"))?
        .extract()?;
    
    let flashcard_dict = dict.get_item("flashcard_content")
        .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyKeyError, _>("Missing flashcard_content"))?
        .downcast::<PyDict>()?;
    
    let front_dict = flashcard_dict.get_item("front")
        .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyKeyError, _>("Missing front"))?
        .downcast::<PyDict>()?;
    
    let back_dict = flashcard_dict.get_item("back")
        .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyKeyError, _>("Missing back"))?
        .downcast::<PyDict>()?;
    
    let front = CardFace {
        primary_content: front_dict.get_item("primary_content")
            .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyKeyError, _>("Missing primary_content"))?
            .extract()?,
        secondary_content: front_dict.get_item("secondary_content")
            .and_then(|v| v.extract().ok()),
        example: front_dict.get_item("example")
            .and_then(|v| v.extract().ok()),
        pronunciation: front_dict.get_item("pronunciation")
            .and_then(|v| v.extract().ok()),
        notes: front_dict.get_item("notes")
            .and_then(|v| v.extract().ok()),
        media_references: front_dict.get_item("media_references")
            .unwrap_or(&PyList::empty(front_dict.py()).into())
            .extract()?,
    };
    
    let back = CardFace {
        primary_content: back_dict.get_item("primary_content")
            .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyKeyError, _>("Missing primary_content"))?
            .extract()?,
        secondary_content: back_dict.get_item("secondary_content")
            .and_then(|v| v.extract().ok()),
        example: back_dict.get_item("example")
            .and_then(|v| v.extract().ok()),
        pronunciation: back_dict.get_item("pronunciation")
            .and_then(|v| v.extract().ok()),
        notes: back_dict.get_item("notes")
            .and_then(|v| v.extract().ok()),
        media_references: back_dict.get_item("media_references")
            .unwrap_or(&PyList::empty(back_dict.py()).into())
            .extract()?,
    };
    
    let flashcard_content = FlashcardContent {
        front,
        back,
        tags: flashcard_dict.get_item("tags")
            .unwrap_or(&PyList::empty(flashcard_dict.py()).into())
            .extract()?,
        deck_name: flashcard_dict.get_item("deck_name")
            .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyKeyError, _>("Missing deck_name"))?
            .extract()?,
        card_type: flashcard_dict.get_item("card_type")
            .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyKeyError, _>("Missing card_type"))?
            .extract::<String>()?
            .parse()
            .map_err(|_| PyErr::new::<pyo3::exceptions::PyValueError, _>("Invalid card_type"))?,
    };
    
    let tsv_output: String = dict.get_item("tsv_output")
        .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyKeyError, _>("Missing tsv_output"))?
        .extract()?;
    
    Ok(Stage2Result {
        vocabulary_id,
        stage1_cache_key,
        request_id,
        cache_key,
        flashcard_content,
        tsv_output,
        created_at: Utc::now(),
    })
}

impl std::str::FromStr for FrequencyLevel {
    type Err = String;
    
    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s.to_lowercase().as_str() {
            "verycommon" | "very_common" => Ok(FrequencyLevel::VeryCommon),
            "common" => Ok(FrequencyLevel::Common),
            "uncommon" => Ok(FrequencyLevel::Uncommon),
            "rare" => Ok(FrequencyLevel::Rare),
            "archaic" => Ok(FrequencyLevel::Archaic),
            _ => Err(format!("Invalid frequency level: {}", s)),
        }
    }
}

impl std::str::FromStr for FormalityLevel {
    type Err = String;
    
    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s.to_lowercase().as_str() {
            "veryformal" | "very_formal" => Ok(FormalityLevel::VeryFormal),
            "formal" => Ok(FormalityLevel::Formal),
            "neutral" => Ok(FormalityLevel::Neutral),
            "informal" => Ok(FormalityLevel::Informal),
            "veryinformal" | "very_informal" => Ok(FormalityLevel::VeryInformal),
            _ => Err(format!("Invalid formality level: {}", s)),
        }
    }
}

impl std::str::FromStr for CardType {
    type Err = String;
    
    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s.to_lowercase().as_str() {
            "basic" => Ok(CardType::Basic),
            "basicreversed" | "basic_reversed" => Ok(CardType::BasicReversed),
            "cloze" => Ok(CardType::Cloze),
            "production" => Ok(CardType::Production),
            "recognition" => Ok(CardType::Recognition),
            _ => Err(format!("Invalid card type: {}", s)),
        }
    }
}

#[cfg(feature = "pyo3")]
#[pymodule]
fn flashcard_core(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<PyVocabularyItem>()?;
    Ok(())
}