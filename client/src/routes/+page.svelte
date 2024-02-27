<script lang="ts">
  import { Container } from 'postcss';
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

<section class="p-2  bg-orange-600 text-white">
<h1 class="text-3xl">
  ChatDDx -  Differentialdiagnostiskt beslutsstöd för läkare
</h1>
</section>
<section class="p-2 form-control max-w-full center container mx-auto ">
  <div class=" ">Ange patientens symtom, bakgrund och undersökningsfynd</div>
  <label class="form-control center container mx-auto">
    <div class="label">
    </div>
    <textarea
        id="user-prompt"
        rows="7"
        class="p-0 textarea textarea-primary textarea-md leading-tight"
        placeholder="Ange relevant patientdata"
        ></textarea>
        <modal Container >
         <button class="btn my-0.5 textarea-primary text-xs" onclick="my_modal_1.showModal()">Disclaimer</button>
  <dialog id="my_modal_1" class="modal ">  
    <div class="modal-box max-w-full">
      <h3 class="font text-med">  <table>
        <tr>
            <table>
                <tr>
                    <th>Disclaimer</th>
                </tr>
                <tr>
                    <td align="left">Denna applikation använder ChatGPT via API för att generera potentiella differentialdiagnoser baserade på användarens angivna information.</td>
                </tr>
                <tr>
                    <td align="left">Det är av yttersta vikt att förstå att informationen som tillhandahålls av denna applikation inte ersätter professionell medicinsk rådgivning, diagnos eller behandling.</td>
                </tr>
                <tr>
                    <td align="left">De genererade differentialdiagnoserna är resultatet av algoritmer, inklusive maskininlärning, och bör ses som förslag för vidare utforskning snarare än definitiva slutsatser.</td>
                </tr>
                <tr>
                    <td align="left">Användare uppmanas starkt att rådfråga kvalificerad vårdpersonal för korrekt diagnos och personlig medicinsk rådgivning.</td>
                </tr>
                <tr>
                    <td align="left">Utvecklarna och leverantörerna av denna applikation, inklusive ChatGPT, tar inget ansvar för noggrannheten, fullständigheten eller tillförlitligheten hos informationen som genereras av denna applikation.</td>
                </tr>
                <tr>
                    <td align="left">Användare bör alltid använda sitt eget omdöme och söka medicinsk hjälp från kvalificerad vårdpersonal när de fattar medicinska diagnostiska beslut.</td>
                </tr>
                <tr>
                    <td align="left">Genom att använda denna applikation erkänner användare att applikationen inte är en ersättning för professionell medicinsk kompetens och att utvecklarna och leverantörerna inte är ansvariga för några åtgärder som vidtas baserat på den tillhandahållna informationen.</td> 
                </tr>
                <tr>
                    <td align="left">Copyright © 2023 ChatDDX</td>
                </tr>
            </table></h3>
      <p class="py-4"></p>
      <div class="modal-action">
        <form method="dialog">
          <button class="btn">Jag accepterar villkoren</button>
        </form>
      </div>
    </div>
  </dialog>

  <button class="btn my-2 textarea-primary text-xs " onclick="my_modal_2.showModal()">Information ℹ️</button>
  <dialog id="my_modal_2" class="modal">  
    <div class="modal-box max-w-full">
      <h3 class="font text-med">  <table>
        <tr>
          <table>
            <tr>
                <th>Förslag till inmatning av patientdata</th>
            </tr>
            <tr>
                <td>Exempel 1: Tidigare frisk patient som insjuknat med buksmärta, feber, diarréer och kräkningar efter buffémåltid. Status med nedsatt allmäntillstånd, takykardi, feber och generell buksmärta. CRP 178, leukocytos och blodgas med metabol acidos med hyperkalemi och njursvikt.</td>
            </tr>
            <tr>
                <td>Exempel 2: 67-årig man med tidigare hjärtsvikt, tidigare hjärtinfarkt, hypertoni och diabetes. Inkommer nu med plötslig debut av retrosternal bröstsmärta, andnöd och svettning. Normalt EKG men förhöjt troponin.</td>
            </tr>
            <tr>
                <td>Exempel 3: 21-årig tidigare frisk kvinna inkommer med långsamt insättande lågt sittande buksmärta med illamående och kräkningar. I status AT ua, palpöm i vänster fossa, normalt CRP och urinsticka.</td> 
            </tr>
        </table></h3>
      <p class="py-4"></p>
      <div class="modal-action">
        <form method="dialog">
          <button class="btn">OK </button>
        </form>
      </div>
    </div>
  </dialog>
</modal>
  <div class="flex py-2">
    <button id="query-button" class="btn btn-primary mr-4" on:click={()=>run(data.oai.diagnoses)}>Generera differentialdiagnoser</button>
    <span id="query-loading" class="loading loading-spinner loading-lg text-secondary hidden"></span>
  </div>



  <div class="">Differentialdiagnoser</div> 
  <pre id="response" class="whitespace-pre-wrap break-words center: true,max-w-prose bg-base-200 rounded-lg min-h-64 p-2"></pre>
</section>
