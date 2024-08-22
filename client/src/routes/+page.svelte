<script lang="ts">
import { useChat } from 'ai/svelte';
import { get } from 'svelte/store';
import type { ChatRequestOptions, } from '$lib/ai-types.ts';
import type { PageData } from './$types';

export let data: PageData;
const content = data.content;

let form: HTMLFormElement;

const { input, append, messages, isLoading } = useChat({
  api: 'api/openai',
});

const handleSubmit = (e: any, options: ChatRequestOptions = {}) => {
    e.preventDefault();
    const inputValue = get(input);
    if (!inputValue) return;

    append(
      {
        content: inputValue,
        role: 'user',
        createdAt: new Date(),
      },
      options,
    );
  };

$: assistantMessages = $messages.filter(m => m.role === 'assistant');

</script>

<section class="p-2 bg-blue-600 flex">
  <h1 class="text-3xl text-white grow">
    {content.title}
  </h1>
  <div>
    <form bind:this={form} action="?/setlang&redirectTo=/" method="post">
      <select class="select select-bordered" name="lang" on:change={() => form.requestSubmit()}>
        {#each content.languages as [ id, name ]}
          <option value="{id}" selected={content.lang === id}>{name}</option>
        {/each}
      </select>
    </form>
  </div>
</section>

<div class="p-2 space-y-2 lg:p-12 lg:space-y-8">
  <section>
    <form on:submit={handleSubmit}>
      <label class="form-control">
        <div class="label">
          <span class="label-text">{content.promptLabel}</span>
          <span class="label-text-alt">
            <span class="link" onclick="my_modal_2.showModal()">{content.usageOpen}</span>
          </span>
        </div>
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
      </label>
    </form>
  </section>
  <section>
    <div>{content.responseLabel}</div> 
    <pre
      id="user-response"
      class="whitespace-pre-wrap break-words bg-base-200 rounded-lg min-h-64 p-2"
    >{#if assistantMessages.length}{assistantMessages?.at(-1)?.content || ""}{/if}</pre>
  <button id="copy-btn" class="bg-blue-500 text-white p-2 rounded-lg mt-2">
    {content.copyButton}
</button>

<script>
  // Funktion för att kopiera text
  document.getElementById('copy-btn').addEventListener('click', function() {
      const textToCopy = document.getElementById('user-response').innerText;
      navigator.clipboard.writeText(textToCopy).then(() => {
          alert('Texten är kopierad till urklippet!');
      }).catch(err => {
          console.error('Kunde inte kopiera text:', err);
      });
  });
</script>
</section>
  <section>

    <span class="link" onclick="my_modal_1.showModal()">{content.disclaimerOpen}</span>
    <dialog id="my_modal_1" class="modal">
      <div class="modal-box prose">
        {@html content.disclaimerText}
        <div class="modal-action">
          <form method="dialog">
            <button class="btn">{content.disclaimerClose}</button>
          </form>
        </div>
      </div>
      <form method="dialog" class="modal-backdrop">
        <button>close</button>
      </form>
    </dialog>
    <br>

    <dialog id="my_modal_2" class="modal">
      <div class="modal-box prose">
        {@html content.usageText}
        <div class="modal-action">
          <form method="dialog">
            <button class="btn">{content.usageClose}</button>
          </form>
        </div>
      </div>
      <form method="dialog" class="modal-backdrop">
        <button>close</button>
      </form>
    </dialog>
  </section>
</div>
