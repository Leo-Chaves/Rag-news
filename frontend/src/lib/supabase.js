import { createClient } from "@supabase/supabase-js";

const url = import.meta.env.VITE_SUPABASE_URL;
const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

// Sem as variáveis, o site continua funcionando só no modo anônimo
// (o botão "Entrar" não aparece).
export const authEnabled = Boolean(url && anonKey);

export const supabase = authEnabled
  ? createClient(url, anonKey, {
      auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true },
    })
  : null;

export const googleLoginEnabled = import.meta.env.VITE_AUTH_GOOGLE === "true";
