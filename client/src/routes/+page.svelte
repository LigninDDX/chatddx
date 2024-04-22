<script lang="ts">
import { useChat } from 'ai/svelte';
import type { PageData } from './$types';

export let data: PageData;
const content = data.content;
 
const { input, handleSubmit, messages, isLoading } = useChat({
  api: 'api/openai',
});

$: assistantMessages = $messages.filter(m => m.role === 'assistant');

</script>

<section class="p-2 bg-orange-600 text-white">
<h1 class="text-3xl">{content.title}</h1>
</section>
<section class="p-2 form-control max-w-full center container mx-auto leading-tight">
  <div class=" ">{content.promptLabel}</div>
  <label class="form-control center container mx-auto">
    <div class="label"></div>
    <form on:submit={handleSubmit}>
      <textarea
        id="user-prompt"
        rows="7"
        class="p-0 textarea textarea-primary textarea-md leading-tight"
        placeholder="{content.promptPlaceholder}"
        bind:value={$input}
      />
      <div class="flex py-2">
        <button
          id="query-button"
          class="btn btn-primary mr-4"
          type="submit"
          disabled={$isLoading}
        >{content.promptButton}</button>
        <span id="query-loading" class="loading loading-spinner loading-lg text-secondary" class:hidden={!$isLoading}></span>
      </div>
    </form>
    <modal>
      <button class="btn my-0.5 textarea-primary text-xs" onclick="my_modal_1.showModal()">{content.disclaimerOpen}</button>
  <dialog id="my_modal_1" class="modal ">  
    <div class="modal-box max-w-full">
      <p class="py-4">{content.disclaimerText}</p>
      <div class="modal-action">
        <form method="dialog">
          <button class="btn">{content.disclaimerClose}</button>
        </form>
      </div>
    </div>
  </dialog>

  <button class="btn my-2 textarea-primary text-xs " onclick="my_modal_2.showModal()">{content.usageOpen}</button>
  <dialog id="my_modal_2" class="modal">  
        {content.usageText}
          <button class="btn">{content.usageClose}</button>
  </dialog>
</modal>
  <div class="">{content.responseLabel}</div> 
    <pre
      id="user-response"
      class="whitespace-pre-wrap break-words center: true,max-w-prose bg-base-200 rounded-lg min-h-64 p-2"
    >{#if assistantMessages.length}{assistantMessages?.at(-1)?.content || ""}{/if}</pre>
</section>
