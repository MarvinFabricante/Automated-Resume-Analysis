#!/usr/bin/env node
import { spawn } from 'child_process';

// Convert any --host argument (passed by docker-compose) to Next.js -H flag
const rawArgs = process.argv.slice(2);
const cleanArgs = [];

for (let i = 0; i < rawArgs.length; i++) {
  if (rawArgs[i] === '--host') {
    cleanArgs.push('-H');
    if (rawArgs[i + 1]) {
      cleanArgs.push(rawArgs[i + 1]);
      i++;
    }
  } else if (rawArgs[i].startsWith('--host=')) {
    cleanArgs.push('-H', rawArgs[i].split('=')[1]);
  } else {
    cleanArgs.push(rawArgs[i]);
  }
}

// Ensure default port is 5173 (matching project conventions) if not specified
if (!cleanArgs.includes('-p') && !cleanArgs.includes('--port')) {
  cleanArgs.push('-p', process.env.PORT || '5173');
}

// Ensure default host is 0.0.0.0 if not specified
if (!cleanArgs.includes('-H') && !cleanArgs.includes('--hostname')) {
  cleanArgs.push('-H', process.env.HOSTNAME || '0.0.0.0');
}

const child = spawn('npx', ['next', 'dev', ...cleanArgs], {
  stdio: 'inherit',
});

child.on('exit', (code) => {
  process.exit(code ?? 0);
});
