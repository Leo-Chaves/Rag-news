<template>
  <div class="message-wrapper" :class="message.role">
    <!-- Avatar -->
    <div class="avatar" :class="message.role">
      <span v-if="message.role === 'user'">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
          <path d="M12 12a5 5 0 1 0 0-10 5 5 0 0 0 0 10Zm0 2c-5.33 0-8 2.67-8 4v1h16v-1c0-1.33-2.67-4-8-4Z"/>
        </svg>
      </span>
      <span v-else>
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M12 8V4H8"/>
          <rect width="16" height="12" x="4" y="8" rx="2"/>
          <path d="M2 14h2"/>
          <path d="M20 14h2"/>
          <path d="M15 13v2"/>
          <path d="M9 13v2"/>
        </svg>
      </span>
    </div>

    <!-- Bubble -->
    <div class="bubble-wrapper">
      <div class="bubble" :class="message.role">
        <div v-if="message.role === 'assistant' && message.scope && !message.isLoading" class="scope-tag">
          Escopo: {{ formatScope(message.scope) }}
        </div>
        <!-- Typing indicator for loading AI messages -->
        <div v-if="message.isLoading" class="typing-dots">
          <span /><span /><span />
        </div>
        <p v-else class="bubble-text">{{ message.content }}</p>
      </div>

      <!-- Sources -->
      <div v-if="message.sources && message.sources.length" class="sources">
        <span class="sources-label">Fontes:</span>
        <div v-for="src in message.sources" :key="src" class="source-chip">
          <a
            :href="src"
            target="_blank"
            rel="noopener noreferrer"
            class="source-link"
          >
            {{ formatSource(src) }}
          </a>
          <button
            v-if="canSave"
            type="button"
            class="save-source-btn"
            :class="{ saved: isSaved(src) }"
            :disabled="isSaved(src)"
            :title="isSaved(src) ? 'Já salva na sua conta' : 'Salvar notícia na conta'"
            @click="$emit('save-source', src)"
          >
            {{ isSaved(src) ? "✓ Salva" : "🔖 Salvar" }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  message: {
    type: Object,
    required: true,
    // shape: { id, role: 'user'|'assistant', content, sources?, scope?, isLoading? }
  },
  canSave: {
    type: Boolean,
    default: false,
  },
  savedUrls: {
    type: Array,
    default: () => [],
  },
});

defineEmits(["save-source"]);

function isSaved(url) {
  return props.savedUrls.includes(url);
}

function formatSource(url) {
  try {
    return new URL(url).hostname;
  } catch {
    return url;
  }
}

function formatScope(scope) {
  const map = {
    global: "Global (BBC)",
    saved: "Notícias Salvas",
    custom: "Fontes Personalizadas",
    personal_all: "Acervo Pessoal",
  };
  return map[scope] || scope;
}
</script>

<style scoped>
.message-wrapper {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  max-width: 820px;
  width: 100%;
  animation: fadeSlideIn 0.25s ease forwards;
}
.message-wrapper.user {
  flex-direction: row-reverse;
  align-self: flex-end;
}
.message-wrapper.assistant {
  align-self: flex-start;
}

@keyframes fadeSlideIn {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Avatar */
.avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: 50%;
  flex-shrink: 0;
}
.avatar.user {
  background: var(--color-text-secondary);
  color: var(--color-bg-primary);
}
.avatar.assistant {
  background: var(--color-text-primary);
  color: var(--color-bg-primary);
}
.avatar svg {
  width: 18px;
  height: 18px;
}

/* Bubble */
.bubble-wrapper {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  max-width: calc(100% - 50px);
}
.bubble {
  padding: 0.75rem 1rem;
  border-radius: 14px;
  font-size: 0.875rem;
  line-height: 1.65;
}
.bubble.user {
  background: var(--color-user-bubble);
  border: 1px solid rgba(124, 58, 237, 0.3);
  border-bottom-right-radius: 4px;
  color: var(--color-text-primary);
}
.bubble.assistant {
  background: var(--color-ai-bubble);
  border: 1px solid var(--color-border);
  border-bottom-left-radius: 4px;
  color: var(--color-text-primary);
}
.scope-tag {
  font-size: 0.66rem;
  font-weight: 600;
  color: var(--color-accent-light);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 0.35rem;
}
.bubble-text {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
}

/* Typing dots */
.typing-dots {
  display: flex;
  gap: 5px;
  padding: 4px 2px;
}
.typing-dots span {
  width: 8px;
  height: 8px;
  background: var(--color-accent-light);
  border-radius: 50%;
  animation: bounce 1.2s infinite ease-in-out;
}
.typing-dots span:nth-child(1) { animation-delay: 0s; }
.typing-dots span:nth-child(2) { animation-delay: 0.2s; }
.typing-dots span:nth-child(3) { animation-delay: 0.4s; }
@keyframes bounce {
  0%, 80%, 100% {
    transform: translateY(0);
    opacity: 0.5;
  }
  40% {
    transform: translateY(-6px);
    opacity: 1;
  }
}

/* Sources */
.sources {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  align-items: center;
}
.sources-label {
  font-size: 0.7rem;
  color: var(--color-text-muted);
}
.source-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.12rem 0.45rem;
  border-radius: 6px;
  border: 1px solid var(--color-border);
  background: var(--color-bg-secondary);
}
.source-link {
  font-size: 0.7rem;
  color: var(--color-text-secondary);
  text-decoration: none;
  transition: color 0.15s;
}
.source-link:hover {
  color: var(--color-text-primary);
  text-decoration: underline;
}
.save-source-btn {
  background: transparent;
  border: none;
  border-left: 1px solid var(--color-border);
  padding: 0 0 0 0.3rem;
  font-size: 0.66rem;
  color: var(--color-accent-light);
  cursor: pointer;
}
.save-source-btn.saved {
  color: #4ade80;
  cursor: default;
}
</style>
