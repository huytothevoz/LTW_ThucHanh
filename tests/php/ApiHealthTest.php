<?php

namespace Tests;

use App\Http\Middleware\ResolveIdentity;

class ApiHealthTest extends TestCase
{
    public function test_health_endpoint_preserves_the_public_contract(): void
    {
        $this->withoutMiddleware(ResolveIdentity::class)
            ->getJson('/api/health')
            ->assertOk()
            ->assertExactJson([
                'status' => 'ok',
                'app' => 'CrawlInsight',
                'database' => 'sqlite',
            ]);
    }

    public function test_unknown_api_routes_return_json_not_found(): void
    {
        $this->withoutMiddleware(ResolveIdentity::class)
            ->getJson('/api/not-a-route')
            ->assertNotFound()
            ->assertJsonPath('error.code', 'NOT_FOUND');
    }
}
