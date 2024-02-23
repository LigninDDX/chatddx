<script lang="ts">
  import type { PageData } from './$types';
  import OpenAI from "openai";

  export let data: PageData;

  let client = new OpenAI({
    baseURL: data.oai.diagnoses.endpoint,
    apiKey: data.oai.diagnoses.api_key,
    dangerouslyAllowBrowser: true,
    fetch,
  });

  async function run({api_key, endpoint, identifier, ...payload}) {
    let content = document.getElementById('user-prompt').value.trim();
    let button = document.getElementById('query-button');
    let loading = document.getElementById('query-loading');
    let response = document.getElementById('response');

    let result;
    let messages = [...data.oai.diagnoses.messages, { content, role: "user" }];

    response.textContent = "";

    button.disabled = true;
    loading.classList.remove("hidden");

    try {
      result = await client.chat.completions.create({...payload, messages});
    } catch (error) {
      response.textContent = `Error fetching data from OpenAI: ${error.message}`;
      button.disabled = false;
      loading.classList.add("hidden");
      return;
    }

    if (data.oai.diagnoses.stream) {
      for await (const chunk of result) {
        response.textContent = response.textContent + (chunk.choices[0]?.delta?.content || "");
      }
    } else {
      response.textContent = (result.choices[0].message.content || "");
    }
    button.disabled = false;
    loading.classList.add("hidden");
  }

</script>

<section class="p-4">
<h1 class="text-4xl">
  ChatDDx
</h1>
<small class="text-sm">Differentialdiagnostiskt beslutsstöd för läkare</small>

</section>

<section class="p-4">
  <div class="divider divider-start">Patientunderlag</div>
  <label class="form-control">
    <div class="label">
    </div>
    <textarea
        id="user-prompt"
        rows="7"
        class="textarea textarea-primary textarea-md w-full max-w-prose"
        placeholder="Skriv patientens symtom, bakgrund och undersökningsfynd"
        ></textarea>
  </label>

  <div class="flex py-2">
    <button id="query-button" class="btn btn-primary mr-4" on:click={()=>run(data.oai.diagnoses)}>Generera differentialdiagnoser</button>
    <span id="query-loading" class="loading loading-ball loading-lg hidden"></span>
  </div>
</section>


<section class="p-4">
  <div class="divider divider-start">Differentialdiagnoser</div>
  <pre id="response" class="whitespace-pre-wrap break-words max-w-prose bg-base-200 rounded-lg min-h-64 p-2"></pre>
</section>
