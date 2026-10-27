import { computed, ref } from "vue";
import axios from "axios";

// Estado global
const allTopics = ref([]); // [{ slug, name, parent }]
const selected = ref([]); // slugs salvos no perfil
const loaded = ref(false);

async function loadTopics() {
  if (allTopics.value.length) return;
  try {
    const { data } = await axios.get("/topics");
    allTopics.value = data.topics || [];
  } catch {
    allTopics.value = [];
  }
}

async function loadPreferences() {
  await loadTopics();
  const { data } = await axios.get("/me/preferences");
  selected.value = data.topics || [];
  loaded.value = true;
}

async function savePreferences(slugs) {
  const { data } = await axios.put("/me/preferences", { topics: slugs });
  selected.value = data.topics || [];
  loaded.value = true;
}

function clearPreferences() {
  selected.value = [];
  loaded.value = false;
}

export function usePreferences() {
  const parents = computed(() => allTopics.value.filter((t) => !t.parent));
  const childrenOf = (slug) => allTopics.value.filter((t) => t.parent === slug);
  const nameOf = (slug) => allTopics.value.find((t) => t.slug === slug)?.name || slug;
  const selectedNames = computed(() => selected.value.map(nameOf));

  return {
    allTopics,
    parents,
    childrenOf,
    nameOf,
    selected,
    selectedNames,
    loaded,
    loadTopics,
    loadPreferences,
    savePreferences,
    clearPreferences,
  };
}
