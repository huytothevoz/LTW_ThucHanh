<?php

namespace App\Http\Controllers;

use App\Support\TwigRenderer;
use Illuminate\Http\Request;
use Symfony\Component\HttpFoundation\Response;

class PageController
{
    public function __construct(private readonly TwigRenderer $views)
    {
    }

    public function show(
        Request $request,
        string $template,
        ?string $activePage = null,
        array $context = [],
    ): Response
    {
        if (in_array($template, ['auth.html'], true) && $request->attributes->get('current_user')
            && in_array($request->path(), ['login', 'register'], true)) {
            return redirect('/workspace');
        }

        return response($this->views->render(
            $request,
            $template,
            array_merge($context, ['active_page' => $activePage]),
        ));
    }

    public function login(Request $request): Response
    {
        return $this->show($request, 'auth.html', null, ['mode' => 'login']);
    }

    public function register(Request $request): Response
    {
        return $this->show($request, 'auth.html', null, ['mode' => 'register']);
    }
}
