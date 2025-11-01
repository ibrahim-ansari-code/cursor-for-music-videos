-- Optimize RLS policies for ownership_entities table to prevent per-row function re-evaluation
-- This improves performance by evaluating auth.uid() once per query instead of per row

-- Drop existing policies
DROP POLICY IF EXISTS "Users can view own ownership entities" ON public.ownership_entities;
DROP POLICY IF EXISTS "Users can insert own ownership entities" ON public.ownership_entities;
DROP POLICY IF EXISTS "Users can update own ownership entities" ON public.ownership_entities;
DROP POLICY IF EXISTS "Users can delete own ownership entities" ON public.ownership_entities;

-- Recreate policies with optimized performance (using subqueries)
CREATE POLICY "Users can view own ownership entities" 
ON public.ownership_entities 
FOR SELECT 
TO public 
USING ((SELECT auth.uid()) = user_id);

CREATE POLICY "Users can insert own ownership entities" 
ON public.ownership_entities 
FOR INSERT 
TO public 
WITH CHECK ((SELECT auth.uid()) = user_id);

CREATE POLICY "Users can update own ownership entities" 
ON public.ownership_entities 
FOR UPDATE 
TO public 
USING ((SELECT auth.uid()) = user_id) 
WITH CHECK ((SELECT auth.uid()) = user_id);

CREATE POLICY "Users can delete own ownership entities" 
ON public.ownership_entities 
FOR DELETE 
TO public 
USING ((SELECT auth.uid()) = user_id);
