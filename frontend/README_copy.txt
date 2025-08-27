Frontend copy-to-clipboard patch
--------------------------------
Files:
- frontend/script.js   (drop-in replacement; adds 📋 buttons next to each value + Copy JSON)
- frontend/copy.css.snippet  (append to your frontend/style.css)

Usage:
- Replace your frontend/script.js with this one.
- Append CSS from copy.css.snippet to your style.css.
- Ensure index.html has a button with id="copyJson" near the JSON <pre>.
  Example:
    <div class="row"><button id="copyJson">Copy JSON</button></div>
