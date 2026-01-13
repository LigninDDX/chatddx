import { serve } from "https://deno.land/std@0.168.0/http/server.ts";

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    const { symptoms } = await req.json();
    const LOVABLE_API_KEY = Deno.env.get('LOVABLE_API_KEY');
    
    if (!LOVABLE_API_KEY) {
      throw new Error('LOVABLE_API_KEY is not configured');
    }

    console.log('Processing diagnosis request for symptoms:', symptoms);

    const response = await fetch("https://ai.gateway.lovable.dev/v1/chat/completions", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${LOVABLE_API_KEY}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model: "google/gemini-2.5-flash",
        messages: [
          { 
            role: "system", 
            content: `Du är en erfaren akutläkare som hjälper till med differentialdiagnostik. 
            
Din uppgift är att baserat på symtom och anamnes ge en lista med möjliga differentialdiagnoser rankade efter sannolikhet.

VIKTIGT: Detta är ENDAST för utbildnings- och referenssyfte. Ersätter INTE klinisk bedömning.

Svara ALLTID på svenska med följande JSON-format:
{
  "diagnoser": [
    {
      "diagnos": "Diagnosnamn",
      "sannolikhet": "hög/medel/låg",
      "beskrivning": "Kort förklaring varför denna diagnos övervägs",
      "varningsflaggor": ["Lista med allvarliga tecken att vara uppmärksam på"],
      "utredning": ["Förslag på lämplig utredning"]
    }
  ],
  "akut_varning": "Om det finns tecken på livshotande tillstånd, beskriv här. Annars null",
  "sammanfattning": "Kort sammanfattning av differentialdiagnostisk bedömning"
}

Ge 3-6 diagnoser beroende på komplexitet. Prioritera alltid livshotande tillstånd först.` 
          },
          { role: "user", content: symptoms }
        ],
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('AI gateway error:', response.status, errorText);
      
      if (response.status === 429) {
        return new Response(JSON.stringify({ error: "För många förfrågningar. Vänta en stund och försök igen." }), {
          status: 429,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        });
      }
      if (response.status === 402) {
        return new Response(JSON.stringify({ error: "AI-krediter slut. Kontakta administratör." }), {
          status: 402,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        });
      }
      
      throw new Error(`AI gateway error: ${response.status}`);
    }

    const data = await response.json();
    const content = data.choices?.[0]?.message?.content;

    console.log('AI response received');

    // Parse JSON from response
    let diagnosisResult;
    try {
      // Extract JSON from potential markdown code blocks
      const jsonMatch = content.match(/```json\n?([\s\S]*?)\n?```/) || content.match(/\{[\s\S]*\}/);
      const jsonStr = jsonMatch ? (jsonMatch[1] || jsonMatch[0]) : content;
      diagnosisResult = JSON.parse(jsonStr);
    } catch (parseError) {
      console.error('Failed to parse AI response:', parseError);
      diagnosisResult = { raw: content };
    }

    return new Response(JSON.stringify(diagnosisResult), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  } catch (error) {
    console.error('Error in diagnose function:', error);
    const errorMessage = error instanceof Error ? error.message : 'Ett oväntat fel inträffade';
    return new Response(JSON.stringify({ error: errorMessage }), {
      status: 500,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  }
});
