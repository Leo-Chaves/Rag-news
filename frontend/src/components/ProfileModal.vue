<template>
  <transition name="fade">
    <div v-if="open" class="modal-overlay" @click.self="close">
      <div class="modal-content" role="dialog" aria-modal="true" aria-label="Meu perfil">
        <div class="modal-header">
          <h3>{{ onboarding ? "Quais assuntos mais te interessam?" : "Meu perfil" }}</h3>
          <button class="close-btn" title="Fechar" @click="close">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
          </button>
        </div>

        <div class="modal-body">
          <section v-if="!onboarding" class="profile-info">
            <div class="avatar-lg">{{ initial }}</div>
            <div class="profile-fields">
              <label class="field">
                <span>Nome</span>
                <input v-model.trim="name" type="text" maxlength="60" />
              </label>
              <span class="email">{{ user?.email }}</span>
            </div>
          </section>

          <section>
            <p class="section-title">Temas de interesse</p>
            <p class="hint">
              As respostas do chat vão priorizar notícias destes temas. Perguntas sobre
              outros assuntos continuam funcionando normalmente.
            </p>

            <p v-if="!parents.length" class="hint">Carregando temas…</p>

            <div v-for="topic in parents" :key="topic.slug" class="topic-group">
              <button
                type="button"
                class="chip"
                :class="{ on: draft.has(topic.slug) }"
                :aria-pressed="draft.has(topic.slug)"
                @click="toggle(topic.slug)"
              >
                <span class="check">✓</span>{{ topic.name }}
                <span v-if="childrenOf(topic.slug).length" class="chip-sub">(todos)</span>
              </button>

              <div v-if="childrenOf(topic.slug).length" class="children">
                <button
                  v-for="child in childrenOf(topic.slug)"
                  :key="child.slug"
                  type="button"
                  class="chip small"
                  :class="{ on: draft.has(child.slug) || draft.has(topic.slug), implied: draft.has(topic.slug) }"
                  :disabled="draft.has(topic.slug)"
                  :aria-pressed="draft.has(child.slug) || draft.has(topic.slug)"
                  :title="draft.has(topic.slug) ? `Incluído em ${topic.name}` : ''"
                  @click="toggle(child.slug)"
                >
                  <span class="check">✓</span>{{ child.name }}
                </button>
              </div>
            </div>
          </section>

          <p v-if="error" class="feedback error">{{ error }}</p>
        </div>

        <div class="modal-footer">
          <button class="secondary-btn" :disabled="busy" @click="close">
            {{ onboarding ? "Agora não" : "Cancelar" }}
          </button>
          <button class="primary-btn" :disabled="busy" @click="save">
            <span v-if="busy" class="spinner" />
            <span v-else>Salvar</span>
          </button>
        </div>
      </div>
    </div>
  </transition>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { useAuth } from "../composables/useAuth";
import { usePreferences } from "../composables/usePreferences";

const props = defineProps({
  open: { type: Boolean, default: false },
  onboarding: { type: Boolean, default: false }, // primeira vez após o cadastro
});
const emit = defineEmits(["close", "saved"]);

const { user, displayName, updateName } = useAuth();
const { parents, childrenOf, selected, loadTopics, savePreferences } = usePreferences();

const draft = ref(new Set());
const name = ref("");
const busy = ref(false);
const error = ref("");

const initial = computed(() => (name.value || displayName.value || "?").charAt(0).toUpperCase());

watch(
  () => props.open,
  (open) => {
    if (!open) return;
    loadTopics();
    draft.value = new Set(selected.value);
    name.value = displayName.value;
    error.value = "";
  }
);

function toggle(slug) {
  const next = new Set(draft.value);
  if (next.has(slug)) {
    next.delete(slug);
  } else {
    next.add(slug);
    // Marcar o tema "pai" já inclui os filhos: remove os filhos redundantes
    childrenOf(slug).forEach((c) => next.delete(c.slug));
  }
  draft.value = next;
}

function close() {
  if (!busy.value) emit("close");
}

async function save() {
  busy.value = true;
  error.value = "";
  try {
    await savePreferences([...draft.value]);
    if (!props.onboarding && name.value && name.value !== displayName.value) {
      await updateName(name.value);
    }
    emit("saved");
    emit("close");
  } catch (e) {
    error.value = e.response?.data?.detail || e.message || "Não foi possível salvar.";
  } finally {
    busy.value = false;
  }
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(3px);
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.5rem;
}
.modal-content {
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  width: 100%;
  max-width: 520px;
  max-height: calc(100dvh - 3rem);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.modal-header,
.modal-footer {
  display: flex;
  align-items: center;
  padding: 1.1rem 1.5rem;
  background: var(--color-bg-secondary);
  flex-shrink: 0;
}
.modal-header {
  justify-content: space-between;
  border-bottom: 1px solid var(--color-border);
}
.modal-footer {
  justify-content: flex-end;
  gap: 0.6rem;
  border-top: 1px solid var(--color-border);
}
.modal-header h3 {
  margin: 0;
  font-size: 1.05rem;
  color: var(--color-text-primary);
}
.close-btn {
  background: transparent;
  border: none;
  color: var(--color-text-muted);
  cursor: pointer;
  padding: 0;
  display: flex;
}
.close-btn:hover {
  color: var(--color-text-primary);
}
.modal-body {
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  overflow-y: auto;
}

.profile-info {
  display: flex;
  align-items: center;
  gap: 1rem;
}
.avatar-lg {
  width: 52px;
  height: 52px;
  border-radius: 50%;
  background: var(--color-accent);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.3rem;
  font-weight: 700;
  flex-shrink: 0;
}
.profile-fields {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  flex: 1;
  min-width: 0;
}
.email {
  font-size: 0.78rem;
  color: var(--color-text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--color-text-secondary);
}
.field input {
  padding: 0.5rem 0.7rem;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-bg-card);
  color: var(--color-text-primary);
  font-size: 0.9rem;
  font-family: inherit;
  outline: none;
}
.field input:focus {
  border-color: var(--color-accent);
}

.section-title {
  margin: 0 0 0.3rem;
  font-size: 0.68rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--color-text-muted);
}
.hint {
  margin: 0 0 1rem;
  font-size: 0.82rem;
  color: var(--color-text-secondary);
  line-height: 1.5;
}

.topic-group {
  display: inline-flex;
  flex-direction: column;
  gap: 0.5rem;
  margin: 0 0.4rem 0.6rem 0;
  vertical-align: top;
}
.topic-group:has(.children) {
  display: flex;
  padding: 0.75rem;
  border: 1px dashed var(--color-border);
  border-radius: 10px;
  margin-right: 0;
}
.children {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}
.chip {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  align-self: flex-start;
  padding: 0.45rem 0.8rem;
  border: 1px solid var(--color-border);
  border-radius: 99px;
  background: var(--color-bg-card);
  color: var(--color-text-secondary);
  font-size: 0.83rem;
  font-weight: 500;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.15s ease;
}
.chip.small {
  font-size: 0.78rem;
  padding: 0.35rem 0.7rem;
}
.chip:hover:not(:disabled) {
  border-color: var(--color-accent-light);
  color: var(--color-text-primary);
}
.chip .check {
  display: none;
  font-weight: 700;
}
.chip.on {
  background: var(--color-accent);
  border-color: var(--color-accent);
  color: white;
}
.chip.on .check {
  display: inline;
}
.chip.implied {
  opacity: 0.6;
  cursor: default;
}
.chip-sub {
  font-size: 0.72rem;
  opacity: 0.75;
}

.feedback.error {
  margin: 0;
  font-size: 0.82rem;
  padding: 0.55rem 0.75rem;
  border-radius: 8px;
  color: #ef4444;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
}

.primary-btn,
.secondary-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 90px;
  min-height: 38px;
  padding: 0.55rem 1.1rem;
  border-radius: 8px;
  font-weight: 600;
  font-size: 0.86rem;
  cursor: pointer;
}
.primary-btn {
  background: var(--color-accent);
  color: white;
  border: none;
}
.secondary-btn {
  background: transparent;
  color: var(--color-text-secondary);
  border: 1px solid var(--color-border);
}
.primary-btn:disabled,
.secondary-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.spinner {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
