import { computed, ref } from "vue";
import { authEnabled, supabase } from "../lib/supabase";

// Estado global (compartilhado por todos os componentes)
const session = ref(null);
const ready = ref(!authEnabled);
const recoveringPassword = ref(false); // usuário chegou pelo link "esqueci a senha"
const listeners = new Set();
let initialized = false;

const ERROR_MESSAGES = {
  invalid_credentials: "E-mail ou senha incorretos.",
  email_not_confirmed: "Confirme seu e-mail antes de entrar (veja sua caixa de entrada).",
  user_already_exists: "Já existe uma conta com este e-mail.",
  email_exists: "Já existe uma conta com este e-mail.",
  weak_password: "Senha fraca. Use pelo menos 8 caracteres, misturando letras e números.",
  over_email_send_rate_limit: "Muitas tentativas. Aguarde alguns minutos e tente de novo.",
  over_request_rate_limit: "Muitas tentativas. Aguarde alguns minutos e tente de novo.",
  same_password: "A nova senha precisa ser diferente da atual.",
  validation_failed: "Verifique os dados informados.",
};

export function authErrorMessage(error) {
  if (!error) return "";
  return ERROR_MESSAGES[error.code] || error.message || "Erro inesperado. Tente novamente.";
}

export function initAuth() {
  if (!authEnabled || initialized) return;
  initialized = true;

  supabase.auth.getSession().then(({ data }) => {
    session.value = data.session;
    ready.value = true;
  });

  supabase.auth.onAuthStateChange((event, newSession) => {
    session.value = newSession;
    if (event === "PASSWORD_RECOVERY") recoveringPassword.value = true;
    listeners.forEach((fn) => fn(event, newSession));
  });
}

/** Retorna o access token atual (renovado automaticamente pelo supabase-js). */
export async function getAccessToken() {
  if (!authEnabled) return null;
  const { data } = await supabase.auth.getSession();
  return data.session?.access_token ?? null;
}

export function onAuthChange(fn) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

export function useAuth() {
  const user = computed(() => session.value?.user ?? null);
  const displayName = computed(() => {
    const u = user.value;
    if (!u) return "";
    return u.user_metadata?.name || u.user_metadata?.full_name || u.email?.split("@")[0] || "";
  });

  async function signIn(email, password) {
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) throw new Error(authErrorMessage(error));
  }

  /** Retorna true se a conta já está ativa, false se precisa confirmar o e-mail. */
  async function signUp(name, email, password) {
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: { data: { name }, emailRedirectTo: window.location.origin },
    });
    if (error) throw new Error(authErrorMessage(error));
    // Com "Confirm email" ligado o Supabase não devolve sessão e,
    // por segurança, também não acusa e-mail já cadastrado.
    return Boolean(data.session);
  }

  async function signInWithGoogle() {
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: window.location.origin },
    });
    if (error) throw new Error(authErrorMessage(error));
  }

  async function sendPasswordReset(email) {
    const { error } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: window.location.origin,
    });
    if (error) throw new Error(authErrorMessage(error));
  }

  async function updatePassword(password) {
    const { error } = await supabase.auth.updateUser({ password });
    if (error) throw new Error(authErrorMessage(error));
    recoveringPassword.value = false;
  }

  async function updateName(name) {
    const { error } = await supabase.auth.updateUser({ data: { name } });
    if (error) throw new Error(authErrorMessage(error));
  }

  async function signOut() {
    await supabase.auth.signOut();
  }

  return {
    authEnabled,
    ready,
    session,
    user,
    displayName,
    recoveringPassword,
    signIn,
    signUp,
    signInWithGoogle,
    sendPasswordReset,
    updatePassword,
    updateName,
    signOut,
  };
}
