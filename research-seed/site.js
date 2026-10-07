'use strict';
const search = document.querySelector('#search');
const filter = document.querySelector('#filter');
const cards = [...document.querySelectorAll('#cases article')];
function update() {
  const q = search.value.toLocaleLowerCase().trim();
  let count = 0;
  for (const card of cards) {
    card.hidden = !card.textContent.toLocaleLowerCase().includes(q) || (filter.value !== '' && card.dataset.kind !== filter.value);
    if (!card.hidden) count++;
  }
  document.querySelector('#count').textContent = `${count} of ${cards.length} cases`;
  document.querySelector('#empty').hidden = count !== 0;
}
search.addEventListener('input', update);
filter.addEventListener('change', update);
