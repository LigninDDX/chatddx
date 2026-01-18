<script lang="ts">
  import {
    AlertTriangle,
    Beaker,
    ChevronDown,
    ChevronUp,
    TrendingUp,
  } from "lucide-svelte";
  import { Badge } from "$lib/components/ui/badge";
  import { slide } from "svelte/transition";

  // Types
  interface Diagnosis {
    diagnos: string;
    sannolikhet: "hög" | "medel" | "låg";
    beskrivning: string;
    varningsflaggor?: string[];
    utredning?: string[];
  }

  // Props
  let { diagnosis, index }: { diagnosis: Diagnosis; index: number } = $props();

  // State
  let expanded = $state(index === 0);

  // Config mapping
  const probabilityConfig = {
    hög: {
      badge:
        "bg-destructive/10 text-destructive border-destructive/30 hover:bg-destructive/15",
      indicator: "bg-gradient-to-r from-destructive to-destructive/80",
      label: "Hög sannolikhet",
    },
    medel: {
      badge: "bg-warning/10 text-warning border-warning/30 hover:bg-warning/15",
      indicator: "bg-gradient-to-r from-warning to-warning/80",
      label: "Medel sannolikhet",
    },
    låg: {
      badge: "bg-muted text-muted-foreground border-border hover:bg-muted/80",
      indicator:
        "bg-gradient-to-r from-muted-foreground/50 to-muted-foreground/30",
      label: "Låg sannolikhet",
    },
  };

  const config = $derived(probabilityConfig[diagnosis.sannolikhet]);
</script>

<div class="animate-slide-up group" style="animation-delay: {index * 80}ms">
  <div
    class="glass-card rounded-2xl overflow-hidden hover:shadow-2xl hover:shadow-primary/10 transition-all duration-300"
  >
    <div class="h-1 {config.indicator}"></div>

    <button
      class="w-full text-left p-5 cursor-pointer block"
      onclick={() => (expanded = !expanded)}
      aria-expanded={expanded}
    >
      <div class="flex items-start justify-between gap-4">
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-3 mb-3">
            <span
              class="flex items-center justify-center w-8 h-8 rounded-xl bg-gradient-to-br from-primary/20 to-accent/20 text-primary text-sm font-display font-bold"
            >
              {index + 1}
            </span>
            <h3
              class="text-lg font-display font-semibold text-foreground truncate group-hover:text-primary transition-colors"
            >
              {diagnosis.diagnos}
            </h3>
          </div>
          <Badge
            variant="outline"
            class="{config.badge} font-medium transition-colors"
          >
            <TrendingUp class="w-3 h-3 mr-1.5" />
            {config.label}
          </Badge>
        </div>
        <div
          class="p-2 rounded-xl hover:bg-muted/80 transition-colors text-muted-foreground hover:text-foreground"
        >
          {#if expanded}
            <ChevronUp size={20} />
          {:else}
            <ChevronDown size={20} />
          {/if}
        </div>
      </div>
    </button>

    {#if expanded}
      <div
        transition:slide={{ duration: 300 }}
        class="px-5 pb-5 space-y-5 border-t border-border/30 pt-5"
      >
        <p class="text-muted-foreground leading-relaxed">
          {diagnosis.beskrivning}
        </p>

        {#if diagnosis.varningsflaggor && diagnosis.varningsflaggor.length > 0}
          <div
            class="p-4 rounded-xl bg-destructive/5 border border-destructive/20 space-y-3"
          >
            <h4
              class="text-sm font-semibold flex items-center gap-2 text-destructive"
            >
              <AlertTriangle size={16} />
              Varningsflaggor
            </h4>
            <ul class="space-y-2">
              {#each diagnosis.varningsflaggor as flag}
                <li
                  class="text-sm text-muted-foreground flex items-start gap-2"
                >
                  <span
                    class="w-1.5 h-1.5 rounded-full bg-destructive mt-2 flex-shrink-0"
                  ></span>
                  {flag}
                </li>
              {/each}
            </ul>
          </div>
        {/if}

        {#if diagnosis.utredning && diagnosis.utredning.length > 0}
          <div
            class="p-4 rounded-xl bg-primary/5 border border-primary/20 space-y-3"
          >
            <h4
              class="text-sm font-semibold flex items-center gap-2 text-primary"
            >
              <Beaker size={16} />
              Förslag på utredning
            </h4>
            <ul class="space-y-2">
              {#each diagnosis.utredning as item}
                <li
                  class="text-sm text-muted-foreground flex items-start gap-2"
                >
                  <span
                    class="w-1.5 h-1.5 rounded-full bg-primary mt-2 flex-shrink-0"
                  ></span>
                  {item}
                </li>
              {/each}
            </ul>
          </div>
        {/if}
      </div>
    {/if}
  </div>
</div>

