def check_answer(student_answer, correct_answer, question_type="short_answer"):
    """Compare auto-gradable answers while ignoring harmless case/space differences."""
    student = " ".join(str(student_answer or "").strip().lower().split())
    correct = " ".join(str(correct_answer or "").strip().lower().split())
    if question_type in {"essay", "open_ended"}:
        # Essay questions require manual review; keep a deterministic fallback.
        return student == correct and bool(correct)
    if question_type in {"mcq", "multiple_choice", "true_false", "boolean", "short_answer", "single_answer", "open"}:
        return student == correct
    return student == correct
