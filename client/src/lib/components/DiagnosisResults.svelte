<script lang="ts">
  import { FileText, ListChecks, ShieldAlert } from "lucide-svelte";
  import {
    Alert,
    AlertDescription,
    AlertTitle,
  } from "$lib/components/ui/alert";
  import DiagnosisCard from "./DiagnosisCard.svelte";

  // Type Definitions
  interface DiagnosisResult {
    diagnoser?: Array<{
      diagnos: string;
      sannolikhet: "hög" | "medel" | "låg";
      beskrivning: string;
      varningsflaggor?: string[];
      utredning?: string[];
    }>;
    akut_varning?: string | null;
    sammanfattning?: string;
    raw?: string;
  }

  // Props
  export let results: DiagnosisResult;
</script>

{#if results.raw}
  <div class="glass-card rounded-2xl p-6">
    <p class="text-muted-foreground whitespace-pre-wrap">{results.raw}</p>
  </div>
{:else}
  <div class="space-y-6">
    {#if results.akut_varning}
      <Alert
        variant="destructive"
        class="border-destructive/30 bg-destructive/5 rounded-2xl animate-scale-in"
      >
        <ShieldAlert class="h-5 w-5" />
        <AlertTitle class="font-display font-bold text-lg"
          >Akut varning</AlertTitle
        >
        <AlertDescription class="mt-2 text-destructive/90">
          {results.akut_varning}
        </AlertDescription>
      </Alert>
    {/if}

    {#if results.sammanfattning}
      <div
        class="glass-card rounded-2xl p-5 animate-slide-up"
        style="animation-delay: 50ms;"
      >
        <div class="flex items-start gap-4">
          <div class="p-2.5 rounded-xl bg-accent/10 flex-shrink-0">
            <FileText class="h-5 w-5 text-accent" />
          </div>
          <div>
            <h3 class="font-display font-semibold text-foreground mb-2">
              Sammanfattning
            </h3>
            <p class="text-muted-foreground leading-relaxed">
              {results.sammanfattning}
            </p>
          </div>
        </div>
      </div>
    {/if}

    {#if results.diagnoser && results.diagnoser.length > 0}
      <div class="space-y-4">
        <div
          class="flex items-center gap-3 animate-slide-up"
          style="animation-delay: 100ms;"
        >
          <div class="p-2 rounded-xl bg-primary/10">
            <ListChecks class="w-5 h-5 text-primary" />
          </div>
          <h3 class="font-display font-bold text-xl text-foreground">
            Differentialdiagnoser
          </h3>
          <span
            class="px-2.5 py-1 rounded-full bg-primary/10 text-primary text-sm font-semibold"
          >
            {results.diagnoser.length}
          </span>
        </div>

        <div class="space-y-3">
          {#each results.diagnoser as diagnosis, index}
            <DiagnosisCard {diagnosis} {index} />
          {/each}
        </div>
      </div>
    {/if}

    <p
      class="text-xs text-muted-foreground text-center pt-6 border-t border-border/30 animate-fade-in"
    >
      Denna information är endast för utbildnings- och referenssyfte och
      ersätter inte klinisk bedömning.
    </p>
  </div>
{/if}
