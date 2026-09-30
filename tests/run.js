// `npm test`: HTML validation, layout/accessibility audit and behaviour tests.
const { execFileSync } = require('child_process');
const path = require('path');

(async () => {
  let failed = 0;
  console.log('HTML validation');
  try {
    const root = path.resolve(__dirname, '..');
    const cli = path.join(root, 'node_modules', 'html-validate', 'bin', 'html-validate.mjs');
    execFileSync(process.execPath, [cli, 'index.html', 'projects/expressvpn/index.html', 'projects/akg/index.html', 'projects/beyerdynamic/index.html'], { cwd: root, stdio: 'inherit' });
    console.log('  ✓ index.html and all three demo pages are valid');
  } catch (err) {
    console.log('  ✗ html-validate: ' + (err.status ? 'errors above' : err.message));
    failed++;
  }

  for (const [title, file] of [['Layout & accessibility', './layout-a11y'], ['Behaviour', './behaviour'], ['Demo 1 · ExpressVPN', './expressvpn'], ['Demo 2 · AKG dashboard', './akg'], ['Demo 3 · beyerdynamic', './project']]) {
    console.log(title);
    const { fail } = await require(file)();
    failed += fail;
  }
  console.log(failed ? `\nFAILED (${failed})` : '\nAll checks passed');
  process.exit(failed ? 1 : 0);
})().catch(err => { console.error(err); process.exit(1); });
