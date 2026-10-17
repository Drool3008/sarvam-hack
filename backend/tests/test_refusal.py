"""The three refusals are invariants, so they get the strictest tests here.

prompt.md section 12 asks for positive and negative cases in English and in at
least Hindi and Telugu.
"""

from app.assess.refusal import RefusalViolation, enforce, validate

HOUSEHOLD_CONDITIONS = ["high blood pressure", "sugar"]
PRESCRIBED = ["Telmisartan", "Metformin", "Atorvastatin"]


# --- passes --------------------------------------------------------------

def test_plain_status_text_passes():
    v = validate(
        "Telmisartan was ordered and received by Lakshmi.",
        condition_labels=HOUSEHOLD_CONDITIONS,
        prescribed_medicines=PRESCRIBED,
        candidate_medicines=["Telmisartan"],
    )
    assert v.ok, v.violations


def test_refill_reminder_without_a_dose_passes():
    v = validate(
        "Four days of cover left on Metformin. A refill has been arranged.",
        condition_labels=HOUSEHOLD_CONDITIONS,
        prescribed_medicines=PRESCRIBED,
        candidate_medicines=["Metformin"],
    )
    assert v.ok, v.violations


def test_appointment_text_in_telugu_passes():
    # "An appointment has been booked at the clinic tomorrow morning."
    v = validate(
        "రేపు ఉదయం క్లినిక్‌లో అపాయింట్‌మెంట్ బుక్ చేయబడింది.",
        condition_labels=HOUSEHOLD_CONDITIONS,
        prescribed_medicines=PRESCRIBED,
    )
    assert v.ok, v.violations


# --- names a condition ---------------------------------------------------

def test_lexicon_condition_is_caught():
    v = validate("Her diabetes is the likely cause.", prescribed_medicines=PRESCRIBED)
    assert not v.ok
    assert any("names a condition" in x for x in v.violations)


def test_household_label_is_caught_even_though_the_family_entered_it():
    v = validate(
        "This is her sugar acting up again.",
        condition_labels=HOUSEHOLD_CONDITIONS,
        prescribed_medicines=PRESCRIBED,
    )
    assert not v.ok
    assert any("names a condition" in x for x in v.violations)


def test_condition_substring_is_not_a_false_positive():
    # "tb" must not fire inside an ordinary word.
    v = validate("The tablet strip was left on the table.", prescribed_medicines=PRESCRIBED)
    assert not any("names a condition" in x for x in v.violations)


# --- suggests a dose -----------------------------------------------------

def test_mg_dose_is_caught():
    v = validate("Take 500 mg in the morning.", prescribed_medicines=PRESCRIBED)
    assert not v.ok
    assert any("suggests a dose" in x for x in v.violations)


def test_tablet_count_is_caught():
    v = validate("Give her 2 tablets tonight.", prescribed_medicines=PRESCRIBED)
    assert not v.ok
    assert any("suggests a dose" in x for x in v.violations)


def test_frequency_is_caught():
    v = validate("One twice a day until the strip is over.", prescribed_medicines=PRESCRIBED)
    assert not v.ok
    assert any("suggests a dose" in x for x in v.violations)


def test_indian_dose_notation_is_caught():
    v = validate("Follow 1-0-1 from tomorrow.", prescribed_medicines=PRESCRIBED)
    assert not v.ok
    assert any("suggests a dose" in x for x in v.violations)


def test_dose_in_hindi_text_is_caught():
    # "Take 500 mg in the morning."  The unit carries the violation.
    v = validate("सुबह 500 mg लेना है।", prescribed_medicines=PRESCRIBED)
    assert not v.ok
    assert any("suggests a dose" in x for x in v.violations)


def test_dose_in_telugu_text_is_caught():
    # "Two tablets a day."
    v = validate("రోజుకు 2 tablets వేసుకోండి.", prescribed_medicines=PRESCRIBED)
    assert not v.ok
    assert any("suggests a dose" in x for x in v.violations)


def test_a_days_of_cover_figure_is_not_a_dose():
    v = validate("10 days of cover left.", prescribed_medicines=PRESCRIBED)
    assert v.ok, v.violations


def test_a_rupee_figure_is_not_a_dose():
    v = validate("₹240 was paid to the chemist.", prescribed_medicines=PRESCRIBED)
    assert v.ok, v.violations


# --- substitutes a medicine ---------------------------------------------

def test_unprescribed_medicine_is_a_substitution():
    v = validate(
        "Telmisartan is out of stock, so Losartan was arranged instead.",
        prescribed_medicines=PRESCRIBED,
        candidate_medicines=["Telmisartan", "Losartan"],
    )
    assert not v.ok
    assert any("substitutes a medicine" in x for x in v.violations)


def test_prescribed_medicine_is_not_a_substitution():
    v = validate(
        "Telmisartan was ordered from the second chemist.",
        prescribed_medicines=PRESCRIBED,
        candidate_medicines=["Telmisartan"],
    )
    assert v.ok, v.violations


def test_medicine_match_ignores_case():
    v = validate(
        "telmisartan was ordered.",
        prescribed_medicines=PRESCRIBED,
        candidate_medicines=["telmisartan"],
    )
    assert v.ok, v.violations


# --- enforce -------------------------------------------------------------

def test_enforce_returns_clean_text():
    text = "Metformin was received by Lakshmi."
    assert enforce(text, prescribed_medicines=PRESCRIBED) == text


def test_enforce_raises_with_the_verdict_attached():
    try:
        enforce("Take 1 tablet twice a day for her diabetes.", prescribed_medicines=PRESCRIBED)
    except RefusalViolation as exc:
        assert exc.verdict.violations
    else:
        raise AssertionError("a dose and a condition must not pass enforce()")
