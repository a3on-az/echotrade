module.exports = {
  apps: [
    {
      name: 'echotrade-bot',
      script: 'venv/bin/python',
      args: 'main.py --paper',
      cwd: '/Users/hien/projects/echotrade',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '500M',
      env: {
        NODE_ENV: 'production',
        PAPER_TRADING: 'true',
        SANDBOX_MODE: 'true'
      },
      error_file: './logs/echotrade-bot-error.log',
      out_file: './logs/echotrade-bot-out.log',
      log_file: './logs/echotrade-bot-combined.log',
      time: true,
      merge_logs: true
    },
    {
      name: 'echotrade-dashboard',
      script: 'venv/bin/python',
      args: 'app.py',
      cwd: '/Users/hien/projects/echotrade',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '500M',
      env: {
        NODE_ENV: 'production',
        HOST: '0.0.0.0',
        PORT: '8050'
      },
      error_file: './logs/dashboard-error.log',
      out_file: './logs/dashboard-out.log',
      log_file: './logs/dashboard-combined.log',
      time: true,
      merge_logs: true
    },
    {
      name: 'echotrade-api',
      script: 'venv/bin/python',
      args: 'api_server.py',
      cwd: '/Users/hien/projects/echotrade',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '300M',
      env: {
        NODE_ENV: 'production',
        API_PORT: '8000'
      },
      error_file: './logs/api-error.log',
      out_file: './logs/api-out.log',
      log_file: './logs/api-combined.log',
      time: true,
      merge_logs: true
    }
  ]
};
