import { AlertCircle, FileText, ListChecks, ShieldAlert } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { DiagnosisCard } from "./DiagnosisCard";

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

interface DiagnosisResultsProps {
  results: DiagnosisResult;
}

export function DiagnosisResults({ results }: DiagnosisResultsProps) {
  if (results.raw) {
    return (
      <div className="glass-card rounded-2xl p-6">
        <p className="text-muted-foreground whitespace-pre-wrap">{results.raw}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {results.akut_varning && (
        <Alert variant="destructive" className="border-destructive/30 bg-destructive/5 rounded-2xl animate-scale-in">
          <ShieldAlert className="h-5 w-5" />
          <AlertTitle className="font-display font-bold text-lg">Akut varning</AlertTitle>
          <AlertDescription className="mt-2 text-destructive/90">
            {results.akut_varning}
          </AlertDescription>
        </Alert>
      )}

      {results.sammanfattning && (
        <div className="glass-card rounded-2xl p-5 animate-slide-up" style={{ animationDelay: '50ms' }}>
          <div className="flex items-start gap-4">
            <div className="p-2.5 rounded-xl bg-accent/10 flex-shrink-0">
              <FileText className="h-5 w-5 text-accent" />
            </div>
            <div>
              <h3 className="font-display font-semibold text-foreground mb-2">Sammanfattning</h3>
              <p className="text-muted-foreground leading-relaxed">{results.sammanfattning}</p>
            </div>
          </div>
        </div>
      )}

      {results.diagnoser && results.diagnoser.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center gap-3 animate-slide-up" style={{ animationDelay: '100ms' }}>
            <div className="p-2 rounded-xl bg-primary/10">
              <ListChecks className="w-5 h-5 text-primary" />
            </div>
            <h3 className="font-display font-bold text-xl text-foreground">
              Differentialdiagnoser
            </h3>
            <span className="px-2.5 py-1 rounded-full bg-primary/10 text-primary text-sm font-semibold">
              {results.diagnoser.length}
            </span>
          </div>
          <div className="space-y-3">
            {results.diagnoser.map((diagnosis, index) => (
              <DiagnosisCard key={index} diagnosis={diagnosis} index={index} />
            ))}
          </div>
        </div>
      )}

      <p className="text-xs text-muted-foreground text-center pt-6 border-t border-border/30 animate-fade-in">
        Denna information är endast för utbildnings- och referenssyfte och ersätter inte klinisk bedömning.
      </p>
    </div>
  );
}