import { PublicClientApplication } from '@azure/msal-browser';
import msalConfig from './pages/LoginPage/config/msalConfig';

export const msalInstance = new PublicClientApplication(msalConfig);
