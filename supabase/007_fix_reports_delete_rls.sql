DROP POLICY IF EXISTS reports_delete_by_shortlist ON public.reports;

CREATE POLICY reports_delete_by_shortlist ON public.reports
AS PERMISSIVE FOR DELETE
TO authenticated
USING (
  EXISTS (
    SELECT 1
    FROM public.shortlists_items si
    JOIN public.shortlists s ON s.id = si.shortlist_id
    WHERE si.player_id = public.reports.player_id
    -- AND s.owner_id = auth.uid()
  )
);
