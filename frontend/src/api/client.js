import axios from 'axios';

const apiClient = axios.create({
  // Replace the port with the one used by your FastAPI (usually 8000)
  baseURL: 'http://localhost:8000', 
  headers: {
    'Content-Type': 'application/json',
  },
});

export default apiClient;