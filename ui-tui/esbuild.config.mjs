import { build } from 'esbuild';

await build({
  entryPoints: ['src/entry.tsx'],
  bundle: true,
  platform: 'node',
  target: 'node20',
  format: 'esm',
  outfile: 'dist/entry.js',
  external: ['react-devtools-core'],
  banner: {
    js: '#!/usr/bin/env node',
  },
});
