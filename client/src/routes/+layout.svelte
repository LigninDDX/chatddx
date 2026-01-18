<script>
  import "../app.css";
  import { Toaster } from "$lib/components/ui/sonner";

  let { children } = $props();
</script>

<div class="app-container">
  {@render children()}
</div>

<Toaster />
