let allProblems = [];
const PAGE = 20;
let currentPage = 0;

const RATING_COLORS = {
	800: '#aaa', 900: '#aaa', 1000: '#aaa', 1100: '#aaa',
	1200: '#77ff77', 1300: '#77ff77',
	1400: '#77ddbb', 1500: '#77ddbb',
	1600: '#aaaaff', 1700: '#aaaaff', 1800: '#aaaaff',
	1900: '#ff9999', 2000: '#ff9999',
	2100: '#ffbb55', 2200: '#ffbb55', 2300: '#ffbb55',
	2400: '#ffcc88', 2500: '#ffcc88',
	2600: '#ff8888', 2700: '#ff8888', 2800: '#ff8888',
	3000: '#ff0000', 3500: '#ff0000'
};

function ratingColor(r) {
	return RATING_COLORS[r] || '#aaa';
}

function renderCard(p) {
	const rating = p.rating || '?';
	const color = p.rating ? ratingColor(p.rating) : '#555';
	const tags = (p.tags || []).map(t => `<span class="tag">${t}</span>`).join('');
	return `
    <a class="problem-card" href="/problem?contestId=${p.contestId}&index=${p.index}&name=${encodeURIComponent(p.name)}&rating=${p.rating || ''}" target="_blank">
      <div class="card-top">
        <span class="problem-name">${p.name}</span>
        <span class="problem-rating" style="color:${color}">${rating}</span>
      </div>
      <div class="card-tags">${tags}</div>
      <div class="card-id">${p.contestId}${p.index}</div>
    </a>
  `;
}

async function search() {
	hideDropdown('name-dropdown');
	hideDropdown('tag-dropdown');
	hideDropdown('rating-dropdown');

	const name = document.getElementById('name').value;
	const rating = document.getElementById('rating').value;
	const tag = document.getElementById('tag').value;

	const params = new URLSearchParams();
	if (name && name !== "Any name") params.append("name", name);
	if (rating && rating !== "Any rating") params.append("rating", rating);
	if (tag && tag !== "Any tag") params.append("tag", tag);

	const url = params.toString() ? `/problems?${params.toString()}` : `/problems`;

	try {

		const resultsCount = document.getElementById('results-count');
		resultsCount.textContent = "Loading…";
		document.getElementById('results-section').style.display = "block";
		const res = await fetch(url);
		if (!res.ok) throw new Error(`HTTP ${res.status}`);
		allProblems = await res.json();

		currentPage = 0;
		if (allProblems.length === 0) {
			document.getElementById('results-section').style.display = "none";
			document.getElementById('empty').style.display = "block";
			document.getElementById('error').style.display = "none";
			document.getElementById('load-more-wrap').style.display = "none";
			document.getElementById('results-count').textContent = `0 problems found`;
			return;
		}

		document.getElementById('empty').style.display = "none";
		document.getElementById('error').style.display = "none";
		document.getElementById('results-section').style.display = "block";

		renderPage();
	} catch (e) {
		console.error('Search failed:', e);
		document.getElementById('error').style.display = "block";
		document.getElementById('results-section').style.display = "none";
		document.getElementById('empty').style.display = "none";
		document.getElementById('load-more-wrap').style.display = "none";
	}
}

function renderPage() {
	const container = document.getElementById('results');
	const start = currentPage * PAGE;
	const pageItems = allProblems.slice(start, start + PAGE);
	container.innerHTML = pageItems.map(renderCard).join('');

	const total = allProblems.length;
	const from = total === 0 ? 0 : start + 1;
	const to = Math.min(start + PAGE, total);
	document.getElementById('results-count').textContent = `${total} problems found — ${from}–${to}`;

	const controls = document.getElementById('load-more-wrap');
	controls.style.display = total > PAGE ? 'flex' : 'none';

	const prevBtn = document.getElementById('prev-btn');
	const nextBtn = document.getElementById('next-btn');
	if (prevBtn) prevBtn.disabled = currentPage === 0;
	if (nextBtn) nextBtn.disabled = (start + PAGE) >= total;
}

function nextPage() {
	const maxPage = Math.floor((allProblems.length - 1) / PAGE);
	if (currentPage < maxPage) {
		currentPage++;
		renderPage();
		window.scrollTo({ top: 0, behavior: 'smooth' });
	}
}

function prevPage() {
	if (currentPage > 0) {
		currentPage--;
		renderPage();
		window.scrollTo({ top: 0, behavior: 'smooth' });
	}
}

function hideDropdown(id) {
	const dropdown = document.getElementById(id);
	if (!dropdown) return;
	dropdown.innerHTML = '';
	dropdown.style.display = "none";
}

function showDropdown(dropdown, matches, label) {
	matches = [label, ...matches];
	dropdown._matches = matches;
	dropdown.innerHTML = matches.map((x, i) =>
		`<div class="dropdown-item" data-index="${i}">${x}</div>`
	).join('');
	dropdown.style.display = "block";
}

function selectTag(tag) {
	document.getElementById('tag').value = tag;
	hideDropdown('tag-dropdown');
}

function selectName(name) {
	document.getElementById('name').value = name;
	hideDropdown('name-dropdown');
}

function selectRating(rating) {
	document.getElementById('rating').value = rating;
	hideDropdown('rating-dropdown');
}

document.getElementById('tag').addEventListener('focus', function () {
	const dropdown = document.getElementById('tag-dropdown');
	showDropdown(dropdown, CF_TAGS, "Any tag");
});

document.getElementById('tag').addEventListener('input', function () {
	const typed = this.value.toLowerCase();
	const matches = CF_TAGS.filter(t => t.toLowerCase().startsWith(typed));
	const dropdown = document.getElementById('tag-dropdown');
	if (matches.length === 0) {
		dropdown.innerHTML = '';
		return;
	}
	showDropdown(dropdown, matches, "Any tag");
});

document.getElementById('name').addEventListener('focus', function () {
	const dropdown = document.getElementById('name-dropdown');
	showDropdown(dropdown, NAMES, "Any name");
});

document.getElementById('name').addEventListener('input', function () {
	const typed = this.value.toLowerCase();
	const matches = NAMES.filter(t => t.toLowerCase().startsWith(typed));
	const dropdown = document.getElementById('name-dropdown');
	if (matches.length === 0) {
		dropdown.innerHTML = '';
		return;
	}
	showDropdown(dropdown, matches, "Any name");
});

document.getElementById('rating').addEventListener('focus', function () {
	const dropdown = document.getElementById('rating-dropdown');
	showDropdown(dropdown, RATINGS, "Any rating");
});

document.getElementById('rating').addEventListener('input', function () {
	const typed = this.value.toLowerCase();
	const matches = RATINGS.filter(t => t.toString().startsWith(typed));
	const dropdown = document.getElementById('rating-dropdown');
	if (matches.length === 0) {
		dropdown.innerHTML = '';
		return;
	}
	showDropdown(dropdown, matches, "Any rating");
});

document.getElementById('name-dropdown').addEventListener('click', function (e) {
	e.stopPropagation();
	const idx = e.target.dataset.index;
	if (idx !== undefined) {
		selectName(this._matches[idx]);
	}
});

document.getElementById('tag-dropdown').addEventListener('click', function (e) {
	e.stopPropagation();
	const idx = e.target.dataset.index;
	if (idx !== undefined) {
		selectTag(this._matches[idx]);
	}
});

document.getElementById('rating-dropdown').addEventListener('click', function (e) {
	e.stopPropagation();
	const idx = e.target.dataset.index;
	if (idx !== undefined) {
		selectRating(this._matches[idx]);
	}
});

document.addEventListener('click', e => {
	if (!e.target.matches('input')) {
		document.querySelectorAll('.dropdown').forEach(d => d.style.display = "none");
	}
});

document.addEventListener('keydown', e => {
	if (e.key === 'Enter' && e.target && e.target.matches && e.target.matches('input')) {
		e.preventDefault();
		search();
	}
});
