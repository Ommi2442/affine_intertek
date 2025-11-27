import axios from 'axios';
const api = axios.create({
  baseURL: import.meta.env.VITE_BACKEND_URL,
  headers: { 'Content-Type': 'application/json' },
});

class loginService {
  ssouserdata(userInfo) {
    return api
      .post('/sso-login', userInfo)
      .then((response) => {
        return response;
      })
      .catch((err) => {
        console.log(err);
      });
  }
}

export default new loginService();
