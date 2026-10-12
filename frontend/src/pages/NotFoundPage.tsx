import React from 'react'
import { Link } from 'react-router-dom'
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter, Button } from '../components'
import { FileQuestion, Home } from 'lucide-react'

export const NotFoundPage: React.FC = () => {
  return (
    <div className="max-w-md mx-auto py-16 text-center">
      <Card className="shadow-xs">
        <CardHeader className="pb-2">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-slate-100 text-slate-500 mb-3">
            <FileQuestion className="h-8 w-8" />
          </div>
          <CardTitle className="text-2xl text-slate-900">404 — Page Not Found</CardTitle>
          <CardDescription>
            The requested page does not exist or may have been relocated.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-slate-500">
            Please check the URL in your browser or return to the main dashboard.
          </p>
        </CardContent>
        <CardFooter className="justify-center">
          <Link to="/">
            <Button variant="primary" className="flex items-center gap-2">
              <Home className="h-4 w-4" />
              Return Home
            </Button>
          </Link>
        </CardFooter>
      </Card>
    </div>
  )
}
