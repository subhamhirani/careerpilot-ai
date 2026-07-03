'use client';

import { useEffect, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Separator } from '@/components/ui/separator';
import { UserCircle, Save, Plus, X, Github, Linkedin, Globe } from 'phosphor-icons/react';
import { toast } from 'sonner';
import type { UserProfile } from '@/types';

export default function ProfilePage() {
  const queryClient = useQueryClient();
  const [editMode, setEditMode] = useState(false);
  const [form, setForm] = useState<Partial<UserProfile>>({});
  const [newSkill, setNewSkill] = useState('');
  const [newRole, setNewRole] = useState('');

  const { data: profile, isLoading } = useQuery({
    queryKey: ['user-profile'],
    queryFn: () => api.get<UserProfile>('/user-profile'),
  });

  useEffect(() => {
    if (profile) {
      setForm(profile);
    }
  }, [profile]);

  const updateMutation = useMutation({
    mutationFn: (data: Partial<UserProfile>) => api.put<UserProfile>('/user-profile', data),
    onSuccess: (data) => {
      queryClient.setQueryData(['user-profile'], data);
      setEditMode(false);
      toast.success('Profile updated successfully');
    },
    onError: (err) => {
      toast.error(err instanceof Error ? err.message : 'Failed to update profile');
    },
  });

  const handleSave = () => {
    updateMutation.mutate(form);
  };

  const addSkill = () => {
    if (!newSkill.trim()) return;
    setForm((prev) => ({
      ...prev,
      skills: [...(prev.skills || []), newSkill.trim()],
    }));
    setNewSkill('');
  };

  const removeSkill = (idx: number) => {
    setForm((prev) => ({
      ...prev,
      skills: (prev.skills || []).filter((_, i) => i !== idx),
    }));
  };

  const addRole = () => {
    if (!newRole.trim()) return;
    setForm((prev) => ({
      ...prev,
      preferred_roles: [...(prev.preferred_roles || []), newRole.trim()],
    }));
    setNewRole('');
  };

  const removeRole = (idx: number) => {
    setForm((prev) => ({
      ...prev,
      preferred_roles: (prev.preferred_roles || []).filter((_, i) => i !== idx),
    }));
  };

  if (isLoading) {
    return (
      <div className="space-y-6 max-w-3xl">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-3xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <UserCircle className="h-6 w-6" />
            My Profile
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            Your profile is used for job matching and cover letter generation.
          </p>
        </div>
        {!editMode ? (
          <Button onClick={() => setEditMode(true)}>Edit Profile</Button>
        ) : (
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => { setEditMode(false); setForm(profile || {}); }}>
              Cancel
            </Button>
            <Button onClick={handleSave} disabled={updateMutation.isPending}>
              <Save className="h-4 w-4 mr-2" />
              {updateMutation.isPending ? 'Saving...' : 'Save'}
            </Button>
          </div>
        )}
      </div>

      {/* Basic Info */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Basic Information</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label>Full Name</Label>
              {editMode ? (
                <Input value={form.full_name || ''} onChange={(e) => setForm({ ...form, full_name: e.target.value })} />
              ) : (
                <p className="text-sm py-2">{profile?.full_name || <span className="text-muted-foreground">Not set</span>}</p>
              )}
            </div>
            <div className="space-y-2">
              <Label>Phone</Label>
              {editMode ? (
                <Input value={form.phone || ''} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
              ) : (
                <p className="text-sm py-2">{profile?.phone || <span className="text-muted-foreground">Not set</span>}</p>
              )}
            </div>
          </div>
          <div className="space-y-2">
            <Label>Headline</Label>
            {editMode ? (
              <Input value={form.headline || ''} onChange={(e) => setForm({ ...form, headline: e.target.value })} placeholder="e.g. Network Engineer | SOC Analyst" />
            ) : (
              <p className="text-sm py-2">{profile?.headline || <span className="text-muted-foreground">Not set</span>}</p>
            )}
          </div>
          <div className="space-y-2">
            <Label>Summary</Label>
            {editMode ? (
              <Textarea
                value={form.summary || ''}
                onChange={(e) => setForm({ ...form, summary: e.target.value })}
                rows={4}
                placeholder="Brief professional summary..."
              />
            ) : (
              <p className="text-sm py-2 whitespace-pre-wrap">{profile?.summary || <span className="text-muted-foreground">Not set</span>}</p>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Skills */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Skills</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2 mb-3">
            {(form.skills || []).map((skill, idx) => (
              <Badge key={idx} variant="secondary" className="flex items-center gap-1">
                {skill}
                {editMode && (
                  <button onClick={() => removeSkill(idx)} className="ml-1 hover:text-red-500">
                    <X className="h-3 w-3" />
                  </button>
                )}
              </Badge>
            ))}
            {(!form.skills || form.skills.length === 0) && (
              <span className="text-sm text-muted-foreground">No skills added</span>
            )}
          </div>
          {editMode && (
            <div className="flex gap-2">
              <Input
                value={newSkill}
                onChange={(e) => setNewSkill(e.target.value)}
                placeholder="Add a skill..."
                onKeyDown={(e) => e.key === 'Enter' && addSkill()}
              />
              <Button size="sm" onClick={addSkill}>
                <Plus className="h-4 w-4" />
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Preferred Roles */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Preferred Roles</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2 mb-3">
            {(form.preferred_roles || []).map((role, idx) => (
              <Badge key={idx} variant="outline" className="flex items-center gap-1">
                {role}
                {editMode && (
                  <button onClick={() => removeRole(idx)} className="ml-1 hover:text-red-500">
                    <X className="h-3 w-3" />
                  </button>
                )}
              </Badge>
            ))}
            {(!form.preferred_roles || form.preferred_roles.length === 0) && (
              <span className="text-sm text-muted-foreground">No preferred roles added</span>
            )}
          </div>
          {editMode && (
            <div className="flex gap-2">
              <Input
                value={newRole}
                onChange={(e) => setNewRole(e.target.value)}
                placeholder="e.g. SOC Analyst"
                onKeyDown={(e) => e.key === 'Enter' && addRole()}
              />
              <Button size="sm" onClick={addRole}>
                <Plus className="h-4 w-4" />
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Links */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Links</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label className="flex items-center gap-2"><Linkedin className="h-4 w-4" /> LinkedIn</Label>
            {editMode ? (
              <Input value={form.linkedin_url || ''} onChange={(e) => setForm({ ...form, linkedin_url: e.target.value })} placeholder="https://linkedin.com/in/..." />
            ) : (
              <p className="text-sm py-2">{profile?.linkedin_url || <span className="text-muted-foreground">Not set</span>}</p>
            )}
          </div>
          <div className="space-y-2">
            <Label className="flex items-center gap-2"><Github className="h-4 w-4" /> GitHub</Label>
            {editMode ? (
              <Input value={form.github_url || ''} onChange={(e) => setForm({ ...form, github_url: e.target.value })} placeholder="https://github.com/..." />
            ) : (
              <p className="text-sm py-2">{profile?.github_url || <span className="text-muted-foreground">Not set</span>}</p>
            )}
          </div>
          <div className="space-y-2">
            <Label className="flex items-center gap-2"><Globe className="h-4 w-4" /> Portfolio</Label>
            {editMode ? (
              <Input value={form.portfolio_url || ''} onChange={(e) => setForm({ ...form, portfolio_url: e.target.value })} placeholder="https://..." />
            ) : (
              <p className="text-sm py-2">{profile?.portfolio_url || <span className="text-muted-foreground">Not set</span>}</p>
            )}
          </div>
          <Separator />
          <div className="space-y-2">
            <Label>Preferred Location</Label>
            {editMode ? (
              <Input value={form.preferred_location || ''} onChange={(e) => setForm({ ...form, preferred_location: e.target.value })} placeholder="e.g. Remote, Bangalore" />
            ) : (
              <p className="text-sm py-2">{profile?.preferred_location || <span className="text-muted-foreground">Not set</span>}</p>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
