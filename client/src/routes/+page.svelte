<script lang="ts">
  import {
    Stethoscope,
    Loader2,
    AlertTriangle,
    Activity,
    Sparkles,
  } from "lucide-svelte";
  import * as Card from "$lib/components/ui/card";
  import { Button } from "$lib/components/ui/button";
  import { Textarea } from "$lib/components/ui/textarea";
  import { Alert, AlertDescription } from "$lib/components/ui/alert";
  import DiagnosisResults from "$lib/components/DiagnosisResults.svelte";
  import { toast } from "svelte-sonner";
  import { enhance } from "$app/forms";

  // State
  let symptoms = $state("");
  let isLoading = $state(false);
  let results = $state(null);
</script>

<div class="min-h-screen gradient-bg relative overflow-hidden">
  <div class="absolute inset-0 overflow-hidden pointer-events-none">
    <div
      class="absolute top-20 left-10 w-72 h-72 bg-primary/5 rounded-full blur-3xl floating"
    ></div>
    <div
      class="absolute bottom-20 right-10 w-96 h-96 bg-accent/5 rounded-full blur-3xl floating"
      style="animation-delay: -2s"
    ></div>
    <div
      class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-primary/3 rounded-full blur-3xl"
    ></div>
  </div>

  <div class="container max-w-4xl py-10 px-4 sm:py-16 relative z-10">
    <header class="text-center mb-10 sm:mb-14 animate-fade-in">
      <div
        class="inline-flex items-center justify-center w-20 h-20 rounded-3xl bg-gradient-to-br from-primary to-accent mb-6 glow-primary"
      >
        <Stethoscope class="w-10 h-10 text-primary-foreground" />
      </div>
      <h1
        class="text-4xl sm:text-5xl font-display font-bold mb-4 tracking-tight"
      >
        <span class="gradient-text">Akut</span>
        <span class="text-foreground">Differentialdiagnostik</span>
      </h1>
      <p class="text-muted-foreground text-lg max-w-xl mx-auto leading-relaxed">
        Beskriv patientens symtom och anamnes för AI-baserade förslag på
        differentialdiagnoser
      </p>
    </header>

    <Alert
      class="mb-8 glass-card border-warning/20 animate-slide-up"
      style="animation-delay: 100ms"
    >
      <AlertTriangle class="h-5 w-5 text-warning" />
      <AlertDescription class="text-sm text-muted-foreground ml-2">
        <strong class="text-foreground font-semibold">Viktigt:</strong> Detta verktyg
        är endast för utbildnings- och referenssyfte.
      </AlertDescription>
    </Alert>

    <Card.Root
      class="mb-8 glass-card animate-slide-up"
      style="animation-delay: 200ms"
    >
      <Card.Header class="pb-4">
        <div class="flex items-center gap-3">
          <div class="p-2 rounded-xl bg-primary/10">
            <Activity class="w-5 h-5 text-primary" />
          </div>
          <div>
            <Card.Title class="font-display text-xl"
              >Symtom & Anamnes</Card.Title
            >
            <Card.Description class="mt-1">
              Beskriv aktuella symtom, duration, svårighetsgrad, och relevant
              sjukdomshistoria
            </Card.Description>
          </div>
        </div>
      </Card.Header>
      <Card.Content>
        <form
          method="POST"
          action="?/diagnose"
          use:enhance={() => {
            isLoading = true;
            return async ({ result }) => {
              isLoading = false;
              if (result.type === "success") {
                results = result.data.results;
              } else {
                toast.error("Något gick fel. Försök igen.");
              }
            };
          }}
          class="space-y-5"
        >
          <div class="relative">
            <Textarea
              name="symptoms"
              bind:value={symptoms}
              placeholder="Exempel: 65-årig man med plötslig bröstsmärta..."
              class="min-h-[160px] resize-y text-base leading-relaxed bg-background/50 border-border/50 rounded-xl"
              disabled={isLoading}
            />
          </div>
          <div class="flex justify-end">
            <Button
              type="submit"
              disabled={isLoading || !symptoms.trim()}
              size="lg"
              class="gap-2 font-semibold px-6 rounded-xl bg-gradient-to-r from-primary to-primary/90 shadow-lg"
            >
              {#if isLoading}
                <Loader2 class="w-5 h-5 animate-spin" />
                Analyserar...
              {:else}
                <Sparkles class="w-5 h-5" />
                Analysera symtom
              {/if}
            </Button>
          </div>
        </form>
      </Card.Content>
    </Card.Root>

    {#if results}
      <div class="animate-scale-in">
        <DiagnosisResults {results} />
      </div>
    {/if}
  </div>
</div>
