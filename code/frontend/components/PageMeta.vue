<template>
    <div v-if="store.session">
        <Title>
            {{ store.session.name }}
        </Title>
        <link rel="icon" type="image/x-icon" :href="store.session.icon" v-if="store.session.icon" />
    </div>
</template>
<script setup lang="ts">
import { useRoute } from "vue-router";
import { useSessionStore } from "../states/session";
import { computed, watch } from "vue";
import { useHead } from "nuxt/app";

const router = useRoute();
const store = useSessionStore();
// TODO: Replace with proper TS mapping
const { data } = await useAsyncData("post", async () => {
  return await $fetch(useRuntimeConfig().public.basePath + "/rest/metatags?lang=" + router.params.lang);
});
const metatags = data.value.meta
metatags["title"] = data.value.name
useSeoMeta(metatags)

/* set the dark mode as some kind of default if the browser demands is */
if (import.meta.client  && !store.isDarkModeControlledByUser && window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
   store.isDarkMode = true
}

useHead({
  bodyAttrs: {
    "data-bs-theme": () => store.isDarkMode  ? "dark": "light"
  }
})

const isTranslating = computed(() => store.session && store.isTranslating)

watch(isTranslating, value => {
    if (import.meta.client) {
        const haystack = document.getElementsByTagName("body")
        if (haystack.length > 0) {
            if (store.isTranslating) {
                haystack[0].classList.add("is-translating")
                store.getTranslationFeedback()
            } else {
                haystack[0].classList.remove("is-translating")
            }
        }
    }
}, { deep: true, immediate: true })

const isBWMode = computed(() => store.session && store.isBWMode)

watch(isBWMode, value => {
    if (import.meta.client) {
        const haystack = document.getElementsByTagName("body")
        if (haystack.length > 0) {
            if (store.isBWMode) {
                haystack[0].classList.add("a11y-color-bw")
                store.getTranslationFeedback()
            } else {
                haystack[0].classList.remove("a11y-color-bw")
            }
        }
    }
}, { deep: true, immediate: true })
</script>
<style lang="scss">
@import "../style/global.scss";

.a11y-color-bw {
    -webkit-filter: grayscale(100%);
    -moz-filter: grayscale(100%);
    filter: grayscale(100%);
}
</style>