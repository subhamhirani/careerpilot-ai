'use client';

import { useEffect, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useSettingsStore } from '@/lib/store';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Separator } from '@/components/ui/separator';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { toast } from 'sonner';
import { Save, Plus, Trash2, Settings, Search, Bell, Shield, Key, Eye, EyeOff, RefreshCw } from 'lucide-react';
import type { UserSettings, SearchQuery } from '@/types';

interface ApiKeyEntry {
  provider: string;
  key: string;
}

export default function SettingsPage() {
  const queryClient = useQueryClient();
  const { settings, setSettings, loading, setLoading } = useSettingsStore();

  // Local form state
  const [notificationEnabled, setNotificationEnabled] = useState(true);
  const [autoApply, setAutoApply] = useState(false);
  const [maxPerDay, setMaxPerDay] = useState(5);
  const [searchQueries, setSearchQueries] = useState<SearchQuery[]>([]);

  // API Keys state
  const [apiKeys, setApiKeys] = useState<ApiKeyEntry[]>([]);
  const [newProvider, setNewProvider] = useState('');
  const [newApiKey, setNewApiKey] = useState('');
  const [showKeys, setShowKeys] = useState<Record<string, boolean>>({});
  const [addingKey, setAddingKey] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ['settings'],
    queryFn: () => api.get<UserSettings>('/settings'),
  });

  const { data: apiKeysData, isLoading: keysLoading, refetch: refetchKeys } = useQuery({
    queryKey: ['api-keys'],
    queryFn: () => api.get<{ api_keys: ApiKeyEntry[] }>('/settings/api'),
  });

  useEffect(() => {
    if (data) {
      setSettings(data);
      setNotificationEnabled(data.notification_enabled);
      setAutoApply(data.auto_apply);
      setMaxPerDay(data.max_applications_per_day);
      setSearchQueries(data.search_queries || []);
    }
    setLoading(isLoading);
  }, [data, isLoading, setSettings, setLoading]);

  useEffect(() => {
    if (apiKeysData?.api_keys) {
      setApiKeys(apiKeysData.api_keys);
    }
  }, [apiKeysData]);

  const saveMutation = useMutation({
    mutationFn: (body: Partial<UserSettings>) =>
      api.put<UserSettings>('/settings', body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] });
      toast.success('Settings saved successfully');
    },
    onError: (err) => {
      toast.error(err instanceof Error ? err.message : 'Failed to save settings');
    },
  });

  const addKeyMutation = useMutation({
    mutationFn: (body: { provider: string; key: string }) =>
      api.put('/settings/api', body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['api-keys'] });
      refetchKeys();
      setNewProvider('');
      setNewApiKey('');
      setAddingKey(false);
      toast.success('API key added successfully');
    },
    onError: (err) => {
      toast.error(err instanceof Error ? err.message : 'Failed to add API key');
    },
  });

  const deleteKeyMutation = useMutation({
    mutationFn: (provider: string) => api.delete(`/settings/api/${provider}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['api-keys'] });
      refetchKeys();
      toast.success('API key deleted');
    },
    onError: (err) => {
      toast.error(err instanceof Error ? err.message : 'Failed to delete API key');
    },
  });

  const handleSaveGeneral = () => {
    saveMutation.mutate({
      notification_enabled: notificationEnabled,
      auto_apply: autoApply,
      max_applications_per_day: maxPerDay,
    });
  };

  const handleSaveSearch = () => {
    saveMutation.mutate({
      search_queries: searchQueries,
    });
  };

  const handleAddKey = () => {
    if (!newProvider.trim() || !newApiKey.trim()) {
      toast.error('Provider and API key are required');
      return;
    }
    addKeyMutation.mutate({ provider: newProvider.trim().toLowerCase(), key: newApiKey.trim() });
  };

  const handleDeleteKey = (provider: string) => {
    if (confirm(`Delete API key for ${provider}?`)) {
      deleteKeyMutation.mutate(provider);
    }
  };

  const toggleKeyVisibility = (provider: string) => {
    setShowKeys(prev => ({ ...prev, [provider]: !prev[provider] }));
  };

  const addSearchQuery = () => {
    setSearchQueries([
      ...searchQueries,
      {
        id: `new-${Date.now()}`,
        query: '',
        location: '',
        tiers: [],
        sources: [],
        active: true,
      },
    ]);
  };

  const updateSearchQuery = (id: string, field: keyof SearchQuery, value: any) => {
    setSearchQueries(
      searchQueries.map((q) => (q.id === id ? { ...q, [field]: value } : q))
    );
  };

  const removeSearchQuery = (id: string) => {
    setSearchQueries(searchQueries.filter((q) => q.id !== id));
  };

  if (loading && !settings) {
    return (
      <div className="space-y-6">
        <div>
          <Skeleton className="h-8 w-48 mb-2" />
          <Skeleton className="h-4 w-64" />
        </div>
        <Skeleton className="h-96 rounded-lg" />
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground mt-1">
          Configure your CareerPilot preferences
        </p>
      </div>

      <Tabs defaultValue="general" className="space-y-6">
        <TabsList className="flex-wrap">
          <TabsTrigger value="general" className="flex items-center gap-2">
            <Settings className="h-4 w-4" />
            General
          </TabsTrigger>
          <TabsTrigger value="search" className="flex items-center gap-2">
            <Search className="h-4 w-4" />
            Search
          </TabsTrigger>
          <TabsTrigger value="api-keys" className="flex items-center gap-2">
            <Key className="h-4 w-4" />
            API Keys
          </TabsTrigger>
          <TabsTrigger value="notifications" className="flex items-center gap-2">
            <Bell className="h-4 w-4" />
            Notifications
          </TabsTrigger>
        </TabsList>

        <TabsContent value="general" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Application Preferences</CardTitle>
              <CardDescription>
                Configure how CareerPilot handles job applications
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label htmlFor="auto-apply">Auto-Apply</Label>
                  <p className="text-sm text-muted-foreground">
                    Automatically apply to matching jobs without manual approval
                  </p>
                </div>
                <Switch
                  id="auto-apply"
                  checked={autoApply}
                  onCheckedChange={setAutoApply}
                />
              </div>
              <Separator />
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label htmlFor="max-daily">Max Applications Per Day</Label>
                  <p className="text-sm text-muted-foreground">
                    Limit the number of automated applications per day
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Input
                    id="max-daily"
                    type="number"
                    className="w-20 text-center"
                    min={1}
                    max={50}
                    value={maxPerDay}
                    onChange={(e) => setMaxPerDay(parseInt(e.target.value) || 1)}
                  />
                </div>
              </div>
              <Separator />
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label htmlFor="notifications">Email Notifications</Label>
                  <p className="text-sm text-muted-foreground">
                    Receive email notifications for approvals and updates
                  </p>
                </div>
                <Switch
                  id="notifications"
                  checked={notificationEnabled}
                  onCheckedChange={setNotificationEnabled}
                />
              </div>
            </CardContent>
          </Card>

          <div className="flex justify-end">
            <Button onClick={handleSaveGeneral} disabled={saveMutation.isPending}>
              <Save className="h-4 w-4 mr-2" />
              {saveMutation.isPending ? 'Saving...' : 'Save Settings'}
            </Button>
          </div>
        </TabsContent>

        <TabsContent value="search" className="space-y-6">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Search Queries</CardTitle>
                <CardDescription>
                  Manage the search queries CareerPilot uses to find jobs
                </CardDescription>
              </div>
              <Button variant="outline" size="sm" onClick={addSearchQuery}>
                <Plus className="h-4 w-4 mr-1" />
                Add Query
              </Button>
            </CardHeader>
            <CardContent className="space-y-4">
              {searchQueries.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <Search className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">No search queries configured</p>
                  <p className="text-xs">Add a search query to start finding jobs</p>
                </div>
              ) : (
                searchQueries.map((query, index) => (
                  <div key={query.id} className="p-4 border rounded-lg space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">Query {index + 1}</span>
                      <div className="flex items-center gap-2">
                        <Switch
                          checked={query.active}
                          onCheckedChange={(v) => updateSearchQuery(query.id, 'active', v)}
                        />
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-red-500 hover:text-red-700"
                          onClick={() => removeSearchQuery(query.id)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div className="space-y-1">
                        <Label className="text-xs">Keywords</Label>
                        <Input
                          placeholder="e.g. software engineer"
                          value={query.query}
                          onChange={(e) => updateSearchQuery(query.id, 'query', e.target.value)}
                        />
                      </div>
                      <div className="space-y-1">
                        <Label className="text-xs">Location</Label>
                        <Input
                          placeholder="e.g. Remote, New York"
                          value={query.location || ''}
                          onChange={(e) => updateSearchQuery(query.id, 'location', e.target.value)}
                        />
                      </div>
                    </div>
                  </div>
                ))
              )}
            </CardContent>
          </Card>

          <div className="flex justify-end">
            <Button onClick={handleSaveSearch} disabled={saveMutation.isPending}>
              <Save className="h-4 w-4 mr-2" />
              {saveMutation.isPending ? 'Saving...' : 'Save Search Queries'}
            </Button>
          </div>
        </TabsContent>

        <TabsContent value="api-keys" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Key className="h-5 w-5" />
                API Keys
              </CardTitle>
              <CardDescription>
                Manage API keys for job scraping services. Keys are stored securely in the database.
              </CardDescription>
              <div className="mt-2 rounded-lg bg-muted/50 p-3 text-xs space-y-1.5 text-muted-foreground">
                <p><strong>Groq / OpenAI / Gemini</strong> — <span className="font-mono">console.groq.com</span> / <span className="font-mono">platform.openai.com/api-keys</span> / <span className="font-mono">aistudio.google.com</span></p>
                <p><strong>Apify (Indeed)</strong> — <span className="font-mono">console.apify.com</span> → create scraper API token</p>
                <p><strong>LinkedIn</strong> — browser cookies → copy <span className="font-mono">li_at</span> value from linkedin.com</p>
                <p><strong>Naukri</strong> — browser cookies → copy session token from naukri.com</p>
                <p><strong>Telegram</strong> — <span className="font-mono">t.me/BotFather</span> → create bot → copy token</p>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {keysLoading ? (
                <div className="space-y-3">
                  <Skeleton className="h-16 w-full" />
                  <Skeleton className="h-16 w-full" />
                </div>
              ) : apiKeys.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <Key className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">No API keys configured</p>
                  <p className="text-xs">Add API keys for job scraping services</p>
                </div>
              ) : (
                apiKeys.map((entry) => (
                  <div key={entry.provider} className="p-4 border rounded-lg space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Badge variant="secondary" className="text-xs uppercase">
                          {entry.provider}
                        </Badge>
                        <span className="text-sm text-muted-foreground">
                          {showKeys[entry.provider] ? entry.key : entry.key}
                        </span>
                      </div>
                      <div className="flex items-center gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => toggleKeyVisibility(entry.provider)}
                          title={showKeys[entry.provider] ? 'Hide key' : 'Show key'}
                        >
                          {showKeys[entry.provider] ? (
                            <EyeOff className="h-4 w-4" />
                          ) : (
                            <Eye className="h-4 w-4" />
                          )}
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-red-500 hover:text-red-700"
                          onClick={() => handleDeleteKey(entry.provider)}
                          disabled={deleteKeyMutation.isPending}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      <RefreshCw className="h-3 w-3" />
                      <span>Update this key if it expires or hits rate limits</span>
                    </div>
                  </div>
                ))
              )}

              <Separator />

              {!addingKey ? (
                <Button variant="outline" onClick={() => setAddingKey(true)} className="w-full">
                  <Plus className="h-4 w-4 mr-2" />
                  Add API Key
                </Button>
              ) : (
                <div className="p-4 border rounded-lg space-y-3">
                  <h4 className="text-sm font-medium">Add New API Key</h4>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-1">
                      <Label className="text-xs">Provider</Label>
                      <Select value={newProvider} onValueChange={setNewProvider}>
                        <SelectTrigger>
                          <SelectValue placeholder="Select provider..." />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="groq">Groq (LLM)</SelectItem>
                          <SelectItem value="openai">OpenAI (LLM)</SelectItem>
                          <SelectItem value="gemini">Gemini (LLM)</SelectItem>
                          <SelectItem value="apify">Apify (Indeed Scraper)</SelectItem>
                          <SelectItem value="linkedin">LinkedIn (Session Cookie)</SelectItem>
                          <SelectItem value="naukri">Naukri (Session)</SelectItem>
                          <SelectItem value="telegram">Telegram Bot</SelectItem>
                          <SelectItem value="other">Other (custom)</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs">API Key</Label>
                      <Input
                        type="password"
                        placeholder={newProvider === 'linkedin' ? 'li_at=...' : newProvider === 'apify' ? 'apify_api_...' : 'sk-...'}
                        value={newApiKey}
                        onChange={(e) => setNewApiKey(e.target.value)}
                      />
                    </div>
                  </div>
                  <div className="flex justify-end gap-2">
                    <Button variant="ghost" onClick={() => { setAddingKey(false); setNewProvider(''); setNewApiKey(''); }}>
                      Cancel
                    </Button>
                    <Button onClick={handleAddKey} disabled={addKeyMutation.isPending}>
                      {addKeyMutation.isPending ? 'Adding...' : 'Add Key'}
                    </Button>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="notifications" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Notification Preferences</CardTitle>
              <CardDescription>
                Configure how you receive updates about your job search
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>Application Approvals</Label>
                  <p className="text-sm text-muted-foreground">
                    When new applications need your approval
                  </p>
                </div>
                <Switch defaultChecked />
              </div>
              <Separator />
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>Application Submitted</Label>
                  <p className="text-sm text-muted-foreground">
                    When an application is successfully submitted
                  </p>
                </div>
                <Switch defaultChecked />
              </div>
              <Separator />
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>Interview Invitations</Label>
                  <p className="text-sm text-muted-foreground">
                    When you receive an interview invitation
                  </p>
                </div>
                <Switch defaultChecked />
              </div>
              <Separator />
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>Weekly Digest</Label>
                  <p className="text-sm text-muted-foreground">
                    Weekly summary of your job search activity
                  </p>
                </div>
                <Switch defaultChecked />
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
