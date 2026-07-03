'use client';

import { useEffect, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useResumeStore } from '@/lib/store';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { FileText, Upload, Trash2, Star, Download, Plus } from '@phosphor-icons/react';
import { toast } from 'sonner';
import type { Resume } from '@/types';

export default function ResumesPage() {
  const queryClient = useQueryClient();
  const { resumes, setResumes, loading, setLoading } = useResumeStore();
  const [uploadOpen, setUploadOpen] = useState(false);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadName, setUploadName] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['resumes'],
    queryFn: async () => {
      const res = await api.get<{resumes: Resume[]; total: number}>('/resumes');
      return res.resumes || [];
    },
  });

  useEffect(() => {
    if (data) {
      setResumes(Array.isArray(data) ? data : []);
    }
    setLoading(isLoading);
  }, [data, isLoading, setResumes, setLoading]);

  const uploadMutation = useMutation({
    mutationFn: async () => {
      if (!uploadFile) throw new Error('No file selected');
      const formData = new FormData();
      formData.append('file', uploadFile);
      formData.append('name', uploadName || uploadFile.name);
      const res = await fetch('/api/resumes/upload', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${localStorage.getItem('careerpilot_token')}`,
        },
        body: formData,
      });
      if (!res.ok) throw new Error('Upload failed');
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['resumes'] });
      setUploadOpen(false);
      setUploadFile(null);
      setUploadName('');
      toast.success('Resume uploaded successfully');
    },
    onError: (err) => {
      toast.error(err instanceof Error ? err.message : 'Failed to upload resume');
    },
  });

  const setActiveMutation = useMutation({
    mutationFn: (id: string) => api.patch(`/resumes/${id}`, { is_active: true }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['resumes'] });
      toast.success('Active resume updated');
    },
    onError: (err) => {
      toast.error(err instanceof Error ? err.message : 'Failed to update resume');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/resumes/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['resumes'] });
      toast.success('Resume deleted');
    },
    onError: (err) => {
      toast.error(err instanceof Error ? err.message : 'Failed to delete resume');
    },
  });

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setUploadFile(e.target.files[0]);
      if (!uploadName) setUploadName(e.target.files[0].name.replace(/\.[^/.]+$/, ''));
    }
  };

  if (loading && resumes.length === 0) {
    return (
      <div className="space-y-6">
        <div>
          <Skeleton className="h-8 w-48 mb-2" />
          <Skeleton className="h-4 w-64" />
        </div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-48 rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Resumes</h1>
          <p className="text-muted-foreground mt-1">
            Manage your uploaded resumes and CVs
          </p>
        </div>
        <Dialog open={uploadOpen} onOpenChange={setUploadOpen}>
          <DialogTrigger asChild>
            <Button>
              <Upload className="h-4 w-4 mr-2" />
              Upload Resume
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Upload Resume</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 pt-4">
              <div className="space-y-2">
                <Label htmlFor="resume-name">Resume Name</Label>
                <Input
                  id="resume-name"
                  placeholder="My Resume"
                  value={uploadName}
                  onChange={(e) => setUploadName(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="resume-file">File (PDF, DOCX, or TXT)</Label>
                <Input
                  id="resume-file"
                  type="file"
                  accept=".pdf,.docx,.doc,.txt"
                  onChange={handleFileChange}
                />
              </div>
              {uploadFile && (
                <p className="text-sm text-muted-foreground">
                  Selected: {uploadFile.name} ({(uploadFile.size / 1024).toFixed(1)} KB)
                </p>
              )}
              <Button
                className="w-full"
                disabled={!uploadFile || uploadMutation.isPending}
                onClick={() => uploadMutation.mutate()}
              >
                {uploadMutation.isPending ? 'Uploading...' : 'Upload'}
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {resumes.length > 0 ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {resumes.map((resume) => (
            <Card key={resume.id} className={`transition-all hover:shadow-md ${resume.is_active ? 'ring-2 ring-primary/30' : ''}`}>
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2 min-w-0">
                    <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-primary/10 text-primary shrink-0">
                      <FileText className="h-5 w-5" />
                    </div>
                    <div className="min-w-0">
                      <CardTitle className="text-sm truncate">{resume.name}</CardTitle>
                      <p className="text-xs text-muted-foreground">
                        {resume.file_type} • {(resume.file_size / 1024).toFixed(1)} KB
                      </p>
                    </div>
                  </div>
                  {resume.is_active && (
                    <Badge variant="success" className="shrink-0">
                      <Star className="h-3 w-3 mr-1 fill-current" />
                      Active
                    </Badge>
                  )}
                </div>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-1 mb-3">
                  {resume.skills?.slice(0, 5).map((skill, idx) => (
                    <Badge key={idx} variant="secondary" className="text-xs">
                      {skill}
                    </Badge>
                  ))}
                  {(resume.skills?.length ?? 0) > 5 && (
                    <Badge variant="outline" className="text-xs">
                      +{resume.skills!.length - 5} more
                    </Badge>
                  )}
                </div>
                <div className="flex items-center justify-between pt-3 border-t">
                  <div className="flex gap-1">
                    {!resume.is_active && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setActiveMutation.mutate(resume.id)}
                        disabled={setActiveMutation.isPending}
                      >
                        <Star className="h-3.5 w-3.5 mr-1" />
                        Set Active
                      </Button>
                    )}
                    <Button variant="ghost" size="sm" asChild>
                      <a href={`/api/resumes/${resume.id}/download`} download>
                        <Download className="h-3.5 w-3.5" />
                      </a>
                    </Button>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-red-500 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-950"
                    onClick={() => deleteMutation.mutate(resume.id)}
                    disabled={deleteMutation.isPending}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <div className="text-center py-16 border rounded-lg bg-card">
          <FileText className="h-12 w-12 mx-auto mb-4 text-muted-foreground/50" />
          <h3 className="text-lg font-medium">No resumes uploaded</h3>
          <p className="text-muted-foreground text-sm mt-1">
            Upload your first resume to get started with AI-powered applications.
          </p>
          <Button variant="default" className="mt-4" onClick={() => setUploadOpen(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Upload Resume
          </Button>
        </div>
      )}
    </div>
  );
}
