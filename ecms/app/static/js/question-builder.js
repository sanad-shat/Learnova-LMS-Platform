(() => {
  const container = document.getElementById('questionsContainer');
  if (!container) return;
  const counter = document.getElementById('questionCounter');
  const empty = document.getElementById('emptyBuilder');
  const totalScore = document.getElementById('totalScore');
  let serial = 0;

  const labels = {mcq:'Multiple Choice', true_false:'True / False', short_answer:'Short Answer', essay:'Essay'};
  const icons = {mcq:'fa-list-ul', true_false:'fa-toggle-on', short_answer:'fa-pen', essay:'fa-align-left'};

  function refresh() {
    const cards = [...container.querySelectorAll('.question-editor-card')];
    cards.forEach((card, index) => {
      card.querySelector('.question-order').textContent = `QUESTION ${index + 1}`;
    });
    if (counter) counter.textContent = cards.length;
    if (empty) empty.style.display = cards.length ? 'none' : 'grid';
    if (totalScore) {
      const total = cards.reduce((sum, card) => sum + Number(card.querySelector('[data-score]').value || 0), 0);
      totalScore.value = total || 1;
    }
  }

  function addQuestion(type) {
    serial += 1;
    const id = serial;
    const card = document.createElement('article');
    card.className = 'question-editor-card advanced-question-card';
    card.dataset.type = type;
const optionsField = type === 'mcq' ? `
<div class="full-span mcq-builder">

    <div class="mcq-option">
        <input type="radio" name="correct_${id}" value="0" required>
        <span>A</span>
        <input type="text" class="mcq-input" placeholder="Option A">
    </div>

    <div class="mcq-option">
        <input type="radio" name="correct_${id}" value="1">
        <span>B</span>
        <input type="text" class="mcq-input" placeholder="Option B">
    </div>

    <div class="mcq-option">
        <input type="radio" name="correct_${id}" value="2">
        <span>C</span>
        <input type="text" class="mcq-input" placeholder="Option C">
    </div>

    <div class="mcq-option">
        <input type="radio" name="correct_${id}" value="3">
        <span>D</span>
        <input type="text" class="mcq-input" placeholder="Option D">
    </div>

    <input type="hidden" name="options_${id}" class="hidden-options">
    <input type="hidden" name="answer_${id}" class="hidden-answer">

</div>
` : '';
    const trueFalse = type === 'true_false' ? `<label class="full-span">Correct Answer<select name="answer_${id}" required><option value="True">True</option><option value="False">False</option></select></label>` : '';
const normalAnswer = type === 'short_answer'
? `<label class="full-span">
Correct Answer
<input
    name="answer_${id}"
    required
    placeholder="Expected short answer">
</label>`
: '';
    const essayAnswer = type === 'essay' ? `<label class="full-span">Model Answer / Grading Rubric<textarea name="answer_${id}" rows="3" placeholder="Optional rubric for manual grading"></textarea></label>` : '';
    card.innerHTML = `
      <div class="question-editor-head">
        <div class="question-type-title"><span class="question-order">QUESTION</span><strong><i class="fa-solid ${icons[type]}"></i> ${labels[type]}</strong></div>
        <div class="question-card-controls"><button type="button" class="question-move" data-move="up" title="Move up"><i class="fa-solid fa-arrow-up"></i></button><button type="button" class="question-move" data-move="down" title="Move down"><i class="fa-solid fa-arrow-down"></i></button><button type="button" class="icon-delete" title="Delete"><i class="fa-solid fa-trash"></i></button></div>
      </div>
      <input type="hidden" name="type_${id}" value="${type}">
      <div class="form-grid">
        <label class="full-span">Question Text<textarea name="question_${id}" rows="3" required placeholder="Write the question clearly..."></textarea></label>
        <label>Points<input data-score type="number" min="0.5" step="0.5" value="1" name="score_${id}" required></label>
        ${optionsField}${trueFalse}${normalAnswer}${essayAnswer}
      </div>`;
    card.querySelector('.icon-delete').addEventListener('click', () => { card.remove(); refresh(); });
    card.querySelector('[data-move="up"]').addEventListener('click', () => { const prev=card.previousElementSibling; if(prev) container.insertBefore(card,prev); refresh(); });
    card.querySelector('[data-move="down"]').addEventListener('click', () => { const next=card.nextElementSibling; if(next) container.insertBefore(next,card); refresh(); });
    card.querySelector('[data-score]').addEventListener('input', refresh);
    container.appendChild(card);
    refresh();
    card.querySelector('textarea[name^="question_"]').focus();
  }

  document.querySelectorAll('[data-add-type]').forEach(button => button.addEventListener('click', () => addQuestion(button.dataset.addType)));
  const form = document.getElementById('assessmentBuilderForm');

if (form) {
  form.addEventListener('submit', event => {

    if (!container.querySelector('.question-editor-card')) {
      event.preventDefault();
      alert('Please add at least one question.');
      return;
    }

    const mcqBuilders = document.querySelectorAll('.mcq-builder');

    for (const builder of mcqBuilders) {
      const optionInputs = [...builder.querySelectorAll('.mcq-input')];

      const options = optionInputs
        .map(input => input.value.trim())
        .filter(value => value !== '');

      if (options.length < 2) {
        event.preventDefault();
        alert('Please enter at least two choices for each multiple choice question.');
        optionInputs[0]?.focus();
        return;
      }

      const selectedRadio = builder.querySelector(
        'input[type="radio"]:checked'
      );

      if (!selectedRadio) {
        event.preventDefault();
        alert('Please choose the correct answer for each multiple choice question.');
        return;
      }

      const selectedIndex = Number(selectedRadio.value);
      const correctAnswer = optionInputs[selectedIndex]?.value.trim();

      if (!correctAnswer) {
        event.preventDefault();
        alert('The selected correct answer cannot be empty.');
        optionInputs[selectedIndex]?.focus();
        return;
      }

      builder.querySelector('.hidden-options').value = options.join(',');
      builder.querySelector('.hidden-answer').value = correctAnswer;
    }
  });
}

refresh();
})();