module.exports = {
  apps: [
    {
      name: 'frontend-admin',
      script: '/root/institute_admin/frontend/build/index.js',
      env: {
        PORT: 3000,
        PUBLIC_API_BASE_URL: 'https://srv1013493.hstgr.cloud/api/v1'
      }
    },
    {
      name: 'frontend-mobile',
      script: '/root/institute_admin/frontendMobile/build/index.js',
      env: {
        PORT: 3001,
        PUBLIC_API_BASE_URL: 'https://srv1013493.hstgr.cloud/api/v1'
      }
    }
  ]
};

