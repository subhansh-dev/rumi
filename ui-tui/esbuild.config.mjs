import { build } from 'esbuild';
import { copyFileSync, mkdirSync, writeFileSync } from 'fs';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));

// Ensure stubs directory exists and create react-devtools-core stub
mkdirSync(join(__dirname, 'stubs', 'react-devtools-core'), { recursive: true });
writeFileSync(
  join(__dirname, 'stubs', 'react-devtools-core', 'package.json'),
  JSON.stringify({ name: 'react-devtools-core', version: '0.0.0', main: 'index.js' })
);
writeFileSync(
  join(__dirname, 'stubs', 'react-devtools-core', 'index.js'),
  'module.exports = { connectToDevTools: function() {} };\n'
);

// Ensure dist directory exists
mkdirSync(join(__dirname, 'dist'), { recursive: true });

await build({
  entryPoints: ['src/entry.tsx'],
  bundle: true,
  platform: 'node',
  target: 'node20',
  format: 'esm',
  outfile: 'dist/entry.js',
  external: ['react-devtools-core'],
  banner: {
    js: `#!/usr/bin/env node
import { createRequire } from "module";
const require = createRequire(import.meta.url);`,
  },
});

// Copy yoga.wasm to dist for runtime resolution
try {
  copyFileSync(
    join(__dirname, 'node_modules', 'yoga-wasm-web', 'dist', 'yoga.wasm'),
    join(__dirname, 'dist', 'yoga.wasm')
  );
} catch {
  console.warn('[build] Warning: could not copy yoga.wasm');
}
