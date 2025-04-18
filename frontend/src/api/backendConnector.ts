import axios from "axios";

// @ts-ignore
const BACKEND_BASE_PATH = import.meta.env.VITE_BACKEND_BASE_PATH || 'http://localhost:8000';

const AUTH_PATH = `${BACKEND_BASE_PATH}/auth`;


export const login = () => {
    return axios.get<{ redirect_url: string }>(`${AUTH_PATH}/login`, {});
}


